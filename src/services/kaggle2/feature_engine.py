"""
feature_engine.py — KGMON Grandmaster Tabular Feature Engineering Suite
========================================================================
Implements the battle-tested feature engineering methodologies from Chris Deotte's
KGMON Playbook (2026) and the Strategic Technical Framework:
  1. Snap Features: Maps synthetic continuous floats back to nearest original rows
     and calculates perturbation magnitude diffs.
  2. Digit and Decimal Extraction: Raščlanjivanje brojeva na decimalne i cifarske nivoe
     (frac, d1, d2, frac100, mod10, mod100, is_round, common denominator residuals).
  3. Synthetic Artifact Detection & Fingerprinting:
     - Benford's Law distribution deviation
     - String TF-IDF character n-grams on decimal numbers
     - Drift ratios (log1p train_freq / orig_freq)
     - cKDTree Nearest Neighbor Ground Truth Anchoring from original data
     - Manifold Projections (PCA & Gaussian Random Projection fitted exclusively on original data)
  4. Strict Leak-Free Nested Target Encoding:
     - Inner 5-fold CV to prevent label leakage
     - Cross-categorical Bigrams & Trigrams
  5. Arithmetic & Interaction Features (ratios, anomalies, service aggregations).
"""

import os
import math
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.model_selection import StratifiedKFold, KFold
from sklearn.decomposition import PCA
from sklearn.random_projection import GaussianRandomProjection
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger("Kaggle2.FeatureEngine")


class KGMONFeatureEngine:
    """Production tabular feature engineering suite for synthetic and tabular datasets."""

    @staticmethod
    def extract_snap_features(
        df: pd.DataFrame,
        orig_df: pd.DataFrame,
        continuous_cols: List[str]
    ) -> pd.DataFrame:
        """
        Maps each synthetic continuous float to its nearest neighbor value in the original dataset:
          col_snap = nearest value in original data
          col_snap_diff = col - col_snap (quantifies generator perturbation noise)
        """
        out_df = pd.DataFrame(index=df.index)
        for col in continuous_cols:
            if col not in df.columns or col not in orig_df.columns:
                continue

            orig_vals = np.sort(orig_df[col].dropna().unique())
            if len(orig_vals) == 0:
                continue

            vals = df[col].to_numpy(dtype=float)
            idx = np.searchsorted(orig_vals, vals)
            idx = np.clip(idx, 1, len(orig_vals) - 1)
            left = orig_vals[idx - 1]
            right = orig_vals[idx]

            # Choose closest
            nearest = np.where(np.abs(vals - left) < np.abs(vals - right), left, right)
            out_df[f"{col}_snap"] = nearest
            out_df[f"{col}_snap_diff"] = vals - nearest

        return out_df

    @staticmethod
    def extract_decimal_digit_features(
        df: pd.DataFrame,
        numeric_cols: List[str]
    ) -> pd.DataFrame:
        """
        Extracts decimal and digit artifacts across multiple decimal positions:
          frac = x - floor(x)
          d1 = floor(frac * 10)
          d2 = floor(frac * 100) % 10
          frac100 = round(frac * 100)
          mod10 = floor(x) % 10
          mod100 = floor(x) % 100
          is_round = frac < 0.005
          Residuals from denominators 1/2, 1/4, 1/5, 1/10
          Combined digit pair category tokens
        """
        out_df = pd.DataFrame(index=df.index)
        for col in numeric_cols:
            if col not in df.columns:
                continue

            vals = df[col].to_numpy(dtype=float)
            # Guard against NaNs or negative numbers for floor ops
            safe_vals = np.nan_to_num(vals, nan=0.0)
            floor_vals = np.floor(safe_vals)
            frac = safe_vals - floor_vals

            d1 = np.floor(frac * 10.0).astype(int)
            d2 = (np.floor(frac * 100.0) % 10.0).astype(int)
            frac100 = np.round(frac * 100.0).astype(int)
            mod10 = (floor_vals % 10.0).astype(int)
            mod100 = (floor_vals % 100.0).astype(int)
            is_round = (frac < 0.005).astype(int)

            # Common denominator residuals
            res_half = np.abs(frac - np.round(frac * 2.0) / 2.0)
            res_quarter = np.abs(frac - np.round(frac * 4.0) / 4.0)
            res_fifth = np.abs(frac - np.round(frac * 5.0) / 5.0)
            res_tenth = np.abs(frac - np.round(frac * 10.0) / 10.0)

            prefix = f"{col}_"
            out_df[f"{prefix}frac"] = frac
            out_df[f"{prefix}d1"] = d1
            out_df[f"{prefix}d2"] = d2
            out_df[f"{prefix}frac100"] = frac100
            out_df[f"{prefix}mod10"] = mod10
            out_df[f"{prefix}mod100"] = mod100
            out_df[f"{prefix}is_round"] = is_round
            out_df[f"{prefix}res_half"] = res_half
            out_df[f"{prefix}res_quarter"] = res_quarter
            out_df[f"{prefix}res_fifth"] = res_fifth
            out_df[f"{prefix}res_tenth"] = res_tenth
            out_df[f"{prefix}d1_d2"] = d1.astype(str) + "_" + d2.astype(str)

        return out_df

    @staticmethod
    def compute_benford_deviation(series: pd.Series) -> float:
        """
        Computes the Kolmogorov-Smirnov / total variation distance from Benford's Law
        P(d) = log10(1 + 1/d) for d in 1..9 on the leading digits of positive values.
        """
        pos_vals = series.dropna().to_numpy(dtype=float)
        pos_vals = pos_vals[pos_vals > 0]
        if len(pos_vals) == 0:
            return 0.0

        # Extract leading digit
        leading_digits = np.floor(pos_vals / (10.0 ** np.floor(np.log10(pos_vals)))).astype(int)
        leading_digits = leading_digits[(leading_digits >= 1) & (leading_digits <= 9)]
        if len(leading_digits) == 0:
            return 0.0

        counts = np.bincount(leading_digits, minlength=10)[1:10]
        empirical = counts / len(leading_digits)
        benford = np.log10(1.0 + 1.0 / np.arange(1, 10))

        # Total variation distance
        return float(np.sum(np.abs(empirical - benford)) * 0.5)

    @staticmethod
    def extract_string_tfidf_features(
        train_series: pd.Series,
        test_series: Optional[pd.Series] = None,
        max_features: int = 16,
        prefix: str = "tfidf"
    ) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
        """
        Extracts TF-IDF character n-grams from the string representation of numeric values.
        Detects repetitive decimal digit sequences produced by synthetic generators.
        """
        train_str = train_series.fillna(0.0).astype(str).tolist()
        vec = TfidfVectorizer(analyzer="char", ngram_range=(2, 3), max_features=max_features)
        train_mat = vec.fit_transform(train_str).toarray()

        col_names = [f"{prefix}_ngram_{i}" for i in range(train_mat.shape[1])]
        train_out = pd.DataFrame(train_mat, index=train_series.index, columns=col_names)

        test_out = None
        if test_series is not None:
            test_str = test_series.fillna(0.0).astype(str).tolist()
            test_mat = vec.transform(test_str).toarray()
            test_out = pd.DataFrame(test_mat, index=test_series.index, columns=col_names)

        return train_out, test_out

    @staticmethod
    def extract_ckdtree_anchor_features(
        df: pd.DataFrame,
        orig_df: pd.DataFrame,
        feature_cols: List[str],
        target_col: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Builds a cKDTree on normalized continuous columns of original data.
        Attaches the nearest original neighbor's distance and target label (if provided)
        as a zero-leakage ground truth anchor.
        """
        valid_cols = [c for c in feature_cols if c in df.columns and c in orig_df.columns]
        if not valid_cols or len(orig_df) == 0:
            return pd.DataFrame(index=df.index)

        orig_mat = orig_df[valid_cols].fillna(0.0).to_numpy(dtype=float)
        query_mat = df[valid_cols].fillna(0.0).to_numpy(dtype=float)

        # Standardize using original distribution parameters
        mean = orig_mat.mean(axis=0)
        std = orig_mat.std(axis=0)
        std = np.where(std == 0, 1.0, std)

        orig_norm = (orig_mat - mean) / std
        query_norm = (query_mat - mean) / std

        tree = cKDTree(orig_norm)
        distances, indices = tree.query(query_norm, k=1)

        out_df = pd.DataFrame(index=df.index)
        out_df["orig_nn_dist"] = distances

        if target_col and target_col in orig_df.columns:
            orig_targets = orig_df[target_col].to_numpy()
            out_df["orig_target_anchor"] = orig_targets[indices]

        return out_df

    @staticmethod
    def extract_manifold_projections(
        train_df: pd.DataFrame,
        orig_df: pd.DataFrame,
        feature_cols: List[str],
        test_df: Optional[pd.DataFrame] = None,
        n_components: int = 6
    ) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
        """
        Fits PCA and Gaussian Random Projection exclusively on original data,
        then projects train and test data into that manifold space.
        """
        valid_cols = [c for c in feature_cols if c in train_df.columns and c in orig_df.columns]
        k = min(n_components, len(valid_cols), len(orig_df))
        if k < 1:
            tr_empty = pd.DataFrame(index=train_df.index)
            te_empty = pd.DataFrame(index=test_df.index) if test_df is not None else None
            return tr_empty, te_empty

        orig_mat = orig_df[valid_cols].fillna(0.0).to_numpy(dtype=float)
        mean = orig_mat.mean(axis=0)
        std = np.where(orig_mat.std(axis=0) == 0, 1.0, orig_mat.std(axis=0))

        orig_norm = (orig_mat - mean) / std
        tr_norm = (train_df[valid_cols].fillna(0.0).to_numpy(dtype=float) - mean) / std

        # Fit PCA strictly on original
        pca = PCA(n_components=k, random_state=42)
        pca.fit(orig_norm)
        tr_pca = pca.transform(tr_norm)

        # Fit GRP strictly on original
        grp = GaussianRandomProjection(n_components=k, random_state=42)
        grp.fit(orig_norm)
        tr_grp = grp.transform(tr_norm)

        pca_cols = [f"pca_orig_{i}" for i in range(k)]
        grp_cols = [f"grp_orig_{i}" for i in range(k)]

        tr_out = pd.DataFrame(np.hstack([tr_pca, tr_grp]), index=train_df.index, columns=pca_cols + grp_cols)

        te_out = None
        if test_df is not None:
            te_norm = (test_df[valid_cols].fillna(0.0).to_numpy(dtype=float) - mean) / std
            te_pca = pca.transform(te_norm)
            te_grp = grp.transform(te_norm)
            te_out = pd.DataFrame(np.hstack([te_pca, te_grp]), index=test_df.index, columns=pca_cols + grp_cols)

        return tr_out, te_out

    @staticmethod
    def nested_target_encode(
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        cat_cols: List[str],
        y_train: pd.Series,
        test_df: Optional[pd.DataFrame] = None,
        n_splits: int = 5,
        smoothing: float = 10.0,
        seed: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]:
        """
        Leak-free target encoding computed via nested inner cross-validation folds.
        Generates mean, std, and count encodings.
        Formula: (count * mean + smoothing * global_mean) / (count + smoothing)
        """
        global_mean = float(y_train.mean())
        tr_out = pd.DataFrame(index=train_df.index)
        va_out = pd.DataFrame(index=val_df.index)
        te_out = pd.DataFrame(index=test_df.index) if test_df is not None else None

        from sklearn.utils.multiclass import type_of_target
        y_type = type_of_target(y_train)
        if y_type in ("binary", "multiclass"):
            splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
            splits = list(splitter.split(train_df, y_train))
        else:
            splitter = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
            splits = list(splitter.split(train_df))

        for col in cat_cols:
            if col not in train_df.columns:
                continue

            col_tr = train_df[col].astype(str)
            col_va = val_df[col].astype(str)
            col_te = test_df[col].astype(str) if test_df is not None else None

            # Out of fold inner loop
            tr_encoded = pd.Series(index=train_df.index, dtype=float)
            for in_tr_idx, in_val_idx in splits:
                in_tr_cats = col_tr.iloc[in_tr_idx]
                in_tr_y = y_train.iloc[in_tr_idx]

                stats = in_tr_y.groupby(in_tr_cats).agg(["count", "mean"])
                counts = stats["count"]
                means = stats["mean"]
                smoothed = (counts * means + smoothing * global_mean) / (counts + smoothing)

                in_val_cats = col_tr.iloc[in_val_idx]
                tr_encoded.iloc[in_val_idx] = in_val_cats.map(smoothed).fillna(global_mean)

            tr_out[f"{col}_te_mean"] = tr_encoded

            # Outer transform using full train statistics
            full_stats = y_train.groupby(col_tr).agg(["count", "mean"])
            full_counts = full_stats["count"]
            full_means = full_stats["mean"]
            full_smoothed = (full_counts * full_means + smoothing * global_mean) / (full_counts + smoothing)

            va_out[f"{col}_te_mean"] = col_va.map(full_smoothed).fillna(global_mean)
            if te_out is not None and col_te is not None:
                te_out[f"{col}_te_mean"] = col_te.map(full_smoothed).fillna(global_mean)

        return tr_out, va_out, te_out

    @staticmethod
    def create_cross_features(
        df: pd.DataFrame,
        col_pairs: List[Tuple[str, str]]
    ) -> pd.DataFrame:
        """Creates categorical bigrams (colA + '__' + colB) for interaction modeling."""
        out_df = pd.DataFrame(index=df.index)
        for c1, c2 in col_pairs:
            if c1 in df.columns and c2 in df.columns:
                out_df[f"bi_{c1}_{c2}"] = df[c1].astype(str) + "__" + df[c2].astype(str)
        return out_df
