"""
synthetic_features_cookbook.py — Vetted Feature Engineering Recipes for S6E11
==============================================================================
Provides leak-free, production-grade feature engineering functions.
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold


def extract_digit_trie_features(df: pd.DataFrame, amount_col: str = "amount_usd") -> pd.DataFrame:
    """Extracts discrete integer and fractional trie components without leakage."""
    amt = df[amount_col].astype(float)
    df = df.copy()
    df["cents"] = (amt % 1 * 100).round().astype(int)
    df["int_amount"] = amt.astype(int)
    df["scaled_int"] = (amt * 10).astype(int)
    return df


def oof_target_encode_smooth(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    cat_col: str,
    target_series: pd.Series,
    smoothing: float = 10.0,
    n_splits: int = 5,
    random_state: int = 42
) -> tuple[pd.Series, pd.Series]:
    """Applies strict M-estimate target encoding using nested inner KFold."""
    train_out = pd.Series(index=train_df.index, dtype=float)
    global_mean = target_series.mean()

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    for in_tr_idx, in_val_idx in skf.split(train_df, target_series):
        in_tr_cat = train_df.iloc[in_tr_idx][cat_col]
        in_tr_target = target_series.iloc[in_tr_idx]

        stats = in_tr_target.groupby(in_tr_cat).agg(["count", "mean"])
        counts = stats["count"]
        means = stats["mean"]
        smoothed = (counts * means + smoothing * global_mean) / (counts + smoothing)

        in_val_cat = train_df.iloc[in_val_idx][cat_col]
        train_out.iloc[in_val_idx] = in_val_cat.map(smoothed).fillna(global_mean)

    full_stats = target_series.groupby(train_df[cat_col]).agg(["count", "mean"])
    full_smoothed = (full_stats["count"] * full_stats["mean"] + smoothing * global_mean) / (full_stats["count"] + smoothing)
    val_out = val_df[cat_col].map(full_smoothed).fillna(global_mean)

    return train_out, val_out
