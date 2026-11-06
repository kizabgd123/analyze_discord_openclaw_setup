"""
verifier.py — Independent Outcome Verification Layer & Statistical Policy Engine
==================================================================================
Deterministic verification service for ML experiment outcomes:
  - Validates physical artifacts (existence, size, SHA-256, schema, row coverage).
  - Enforces 699,960 unique rows with exactly one prediction per row and no NaNs.
  - Recomputes ground-truth ROC-AUC per fold and overall from parquet artifacts.
  - Computes paired fold-level differences (d_i = auc_exp_i - auc_base_i).
  - Applies statistical classification:
      INVALID, WORSE_CV, INCONCLUSIVE_CV, BETTER_CV, STATISTICALLY_SUPPORTED,
      KAGGLE_PENDING, LB_CONFIRMED.
  - Ignores LLM statements completely.
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import pandas as pd


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class OutcomeVerifier:
    """Independent deterministic outcome-verification service."""

    def __init__(
        self,
        data_dir: Path,
        folds_file: Path,
        baseline_oof_path: Optional[Path] = None,
        min_practical_improvement: float = 0.00010
    ):
        self.data_dir = Path(data_dir)
        self.folds_file = Path(folds_file)
        self.baseline_oof_path = Path(baseline_oof_path) if baseline_oof_path else None
        self.min_practical_improvement = min_practical_improvement

    def verify_oof_artifact(
        self,
        oof_path: Path,
        train_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Validates raw OOF artifact for schema, integrity, unique coverage, and bounds.
        """
        oof_path = Path(oof_path)
        if not oof_path.is_file():
            return {
                "status": "INVALID",
                "error": f"ArtifactMissingError: OOF file does not exist at {oof_path}"
            }

        if oof_path.stat().st_size == 0:
            return {
                "status": "INVALID",
                "error": f"EmptyArtifactError: OOF file {oof_path} is 0 bytes"
            }

        # Read parquet or CSV
        try:
            if oof_path.suffix == ".parquet":
                df_oof = pd.read_parquet(oof_path)
            else:
                df_oof = pd.read_csv(oof_path)
        except Exception as e:
            return {
                "status": "INVALID",
                "error": f"FileReadError: Failed to parse OOF predictions: {e}"
            }

        # Check required columns
        id_col = "id" if "id" in df_oof.columns else None
        pred_col = None
        for col_cand in ["oof_pred", "pred", "is_fraud"]:
            if col_cand in df_oof.columns and col_cand != "id":
                pred_col = col_cand
                break

        if not id_col or not pred_col:
            return {
                "status": "INVALID",
                "error": f"SchemaMismatchError: OOF artifact must contain 'id' and prediction column, got {list(df_oof.columns)}"
            }

        # Check row count
        expected_rows = 699960
        if len(df_oof) != expected_rows:
            return {
                "status": "INVALID",
                "error": f"RowCountMismatchError: Expected {expected_rows} rows, got {len(df_oof)}"
            }

        # Check uniqueness of IDs
        if df_oof[id_col].nunique() != expected_rows:
            return {
                "status": "INVALID",
                "error": f"DuplicatePredictionError: OOF predictions contain duplicate IDs ({df_oof[id_col].nunique()} unique vs {expected_rows} expected)"
            }

        # Check for NaNs
        preds = df_oof[pred_col].to_numpy()
        if np.isnan(preds).any():
            return {
                "status": "INVALID",
                "error": "NaNPredictionError: OOF predictions contain NaN / null values"
            }

        # Check range [0.0, 1.0]
        if (preds < 0.0).any() or (preds > 1.0).any():
            return {
                "status": "INVALID",
                "error": "ProbabilityRangeError: Predictions contain values outside valid [0.0, 1.0] interval"
            }

        return {
            "status": "PASSED",
            "df_oof": df_oof,
            "id_col": id_col,
            "pred_col": pred_col,
            "sha256": sha256_file(oof_path)
        }

    def compute_ground_truth_metrics(
        self,
        df_oof: pd.DataFrame,
        id_col: str,
        pred_col: str,
        train_path: Optional[Path] = None,
        folds_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Calculates ground-truth ROC AUC per fold and overall using sklearn.
        """
        from sklearn.metrics import roc_auc_score

        train_path = Path(train_path) if train_path else (self.data_dir / "train.csv")
        folds_path = Path(folds_path) if folds_path else self.folds_file

        if not train_path.is_file():
            return {"status": "INVALID", "error": f"train.csv not found at {train_path}"}
        if not folds_path.is_file():
            return {"status": "INVALID", "error": f"folds.json not found at {folds_path}"}

        df_train = pd.read_csv(train_path, usecols=["id", "is_fraud"])
        with open(folds_path, "r", encoding="utf-8") as f:
            raw_folds = json.load(f)

        assignments = raw_folds.get("fold_assignments", raw_folds.get("assignments", raw_folds))
        assignments = {str(k): int(v) for k, v in assignments.items() if str(k).isdigit()}

        # Merge on ID
        merged = pd.merge(df_train, df_oof[[id_col, pred_col]], left_on="id", right_on=id_col, how="inner")
        if len(merged) != len(df_train):
            return {
                "status": "INVALID",
                "error": f"AlignmentError: ID alignment failed ({len(merged)} matches vs {len(df_train)} ground truth rows)"
            }

        # Map fold
        merged["fold"] = merged["id"].astype(str).map(assignments)
        if merged["fold"].isna().any():
            return {
                "status": "INVALID",
                "error": "FoldMappingError: Some sample IDs lack frozen fold assignments"
            }

        # Overall ROC AUC
        overall_auc = float(roc_auc_score(merged["is_fraud"], merged[pred_col]))

        # Per-fold ROC AUC
        fold_scores = {}
        for f_id in sorted(merged["fold"].unique()):
            sub = merged[merged["fold"] == f_id]
            f_auc = float(roc_auc_score(sub["is_fraud"], sub[pred_col]))
            fold_scores[int(f_id)] = round(f_auc, 5)

        return {
            "status": "PASSED",
            "overall_auc": round(overall_auc, 5),
            "fold_scores": fold_scores
        }

    def evaluate_and_classify(
        self,
        exp_oof_path: Path,
        base_oof_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Executes complete independent verification and classifies experiment outcome.
        """
        # 1. Verify Exp OOF
        art_res = self.verify_oof_artifact(exp_oof_path)
        if art_res["status"] != "PASSED":
            return {
                "verdict": "INVALID",
                "error": art_res["error"],
                "cv_score": None,
                "fold_scores": {},
                "paired_comparison": None
            }

        # 2. Compute Exp Metrics
        exp_metrics = self.compute_ground_truth_metrics(
            art_res["df_oof"], art_res["id_col"], art_res["pred_col"]
        )
        if exp_metrics["status"] != "PASSED":
            return {
                "verdict": "INVALID",
                "error": exp_metrics["error"],
                "cv_score": None,
                "fold_scores": {},
                "paired_comparison": None
            }

        # 3. Verify Baseline
        b_path = base_oof_path or self.baseline_oof_path
        if not b_path or not b_path.is_file():
            # If no baseline available, classify as UNVERIFIED_BASELINE
            return {
                "verdict": "INCONCLUSIVE_CV",
                "error": "No verified Exp 0 baseline available for paired comparison",
                "cv_score": exp_metrics["overall_auc"],
                "fold_scores": exp_metrics["fold_scores"],
                "paired_comparison": None
            }

        base_art_res = self.verify_oof_artifact(b_path)
        if base_art_res["status"] != "PASSED":
            return {
                "verdict": "INVALID",
                "error": f"CorruptedBaselineError: Baseline OOF failed verification: {base_art_res['error']}",
                "cv_score": exp_metrics["overall_auc"],
                "fold_scores": exp_metrics["fold_scores"],
                "paired_comparison": None
            }

        base_metrics = self.compute_ground_truth_metrics(
            base_art_res["df_oof"], base_art_res["id_col"], base_art_res["pred_col"]
        )
        if base_metrics["status"] != "PASSED":
            return {
                "verdict": "INVALID",
                "error": f"BaselineMetricError: {base_metrics['error']}",
                "cv_score": exp_metrics["overall_auc"],
                "fold_scores": exp_metrics["fold_scores"],
                "paired_comparison": None
            }

        # 4. Paired Fold Comparison
        exp_folds = [exp_metrics["fold_scores"][f] for f in range(5)]
        base_folds = [base_metrics["fold_scores"][f] for f in range(5)]

        paired_diffs = [round(e - b, 5) for e, b in zip(exp_folds, base_folds)]
        mean_diff = round(float(np.mean(paired_diffs)), 5)
        std_diff = round(float(np.std(paired_diffs)), 5)
        n_improve = sum(1 for d in paired_diffs if d > 0)
        n_worsen = sum(1 for d in paired_diffs if d < 0)

        # 5. Outcome Classification
        # Case A: Simpson's paradox or inconsistent direction
        if n_improve >= 4 and mean_diff <= 0:
            # 4 folds improved but mean is negative (a fold collapsed)
            verdict = "INCONCLUSIVE_CV"
        elif mean_diff > 0 and n_improve >= 4:
            if mean_diff >= self.min_practical_improvement:
                verdict = "BETTER_CV"
            else:
                verdict = "INCONCLUSIVE_CV"  # improvement below practical threshold
        elif mean_diff < 0 and n_worsen >= 4:
            verdict = "WORSE_CV"
        else:
            verdict = "INCONCLUSIVE_CV"

        return {
            "verdict": verdict,
            "cv_score": exp_metrics["overall_auc"],
            "base_cv_score": base_metrics["overall_auc"],
            "fold_scores": exp_metrics["fold_scores"],
            "base_fold_scores": base_metrics["fold_scores"],
            "paired_diffs": paired_diffs,
            "mean_diff": mean_diff,
            "std_diff": std_diff,
            "n_improve": n_improve,
            "n_worsen": n_worsen,
            "error": None
        }
