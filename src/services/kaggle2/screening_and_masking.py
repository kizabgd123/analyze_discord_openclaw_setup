"""
screening_and_masking.py — Fast CPU 1-Feature Screening & Score Masking
========================================================================
Implements operational efficiency and competition tactics from the Strategic Framework:
  1. Fast 1-Feature CPU Screening:
     Tests a single candidate engineered feature on CPU before committing to full GPU training.
     Instead of training an entire complex GPU model with N+1 features, builds a fast 1-feature
     model or linear blend. If the single feature does not improve CV, the hypothesis is
     immediately discarded, saving extensive GPU compute.
  2. Upside-Down Predictions (Score Masking):
     Inverts submission probabilities (p_sub = 1 - p) to conceal true leaderboard rank while
     allowing the internal team to decode the real score (1 - public_score).
"""

import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression, RidgeClassifier

logger = logging.getLogger("Kaggle2.ScreeningAndMasking")


def fast_1feature_cpu_screening(
    base_oof_probs: np.ndarray,
    y_true: np.ndarray,
    candidate_feature: pd.Series,
    blend_weight: float = 0.05
) -> Dict[str, Any]:
    """
    Rapidly evaluates if a single candidate feature provides incremental signal over current baseline:
      1. Normalizes the candidate feature on CPU.
      2. Computes the baseline AUC.
      3. Tests if blending or fitting a lightweight logistic regression with the candidate feature
         produces a positive delta CV (delta_cv > 0).
    Returns dict with candidate evaluation, delta_cv, and recommendation (PROCEED or DISCARD).
    """
    base_auc = float(roc_auc_score(y_true, base_oof_probs))
    feat_vals = candidate_feature.fillna(candidate_feature.median() if len(candidate_feature.dropna()) > 0 else 0.0).to_numpy(dtype=float)

    # Standardize feature values
    std = feat_vals.std()
    feat_norm = (feat_vals - feat_vals.mean()) / (std if std != 0 else 1.0)

    # Fast 1-feature logistic regression
    X_feat = feat_norm.reshape(-1, 1)
    lr = LogisticRegression(C=1.0, max_iter=200, solver="lbfgs")
    try:
        lr.fit(X_feat, y_true)
        feat_probs = lr.predict_proba(X_feat)[:, 1]
    except Exception as e:
        logger.warning(f"[FastScreening] Single-feature fit failed: {e}")
        feat_probs = 1.0 / (1.0 + np.exp(-feat_norm))

    single_feat_auc = float(roc_auc_score(y_true, feat_probs))

    # Fast linear blend with base OOF
    blended_probs = (1.0 - blend_weight) * base_oof_probs + blend_weight * feat_probs
    blended_auc = float(roc_auc_score(y_true, blended_probs))
    delta_cv = blended_auc - base_auc

    recommendation = "PROCEED" if delta_cv > 0.00005 else "DISCARD"

    return {
        "base_auc": base_auc,
        "single_feat_auc": single_feat_auc,
        "blended_auc": blended_auc,
        "delta_cv": delta_cv,
        "recommendation": recommendation,
        "worth_gpu_full_train": delta_cv > 0.00005
    }


def mask_submission_predictions(probs: np.ndarray) -> np.ndarray:
    """
    Conceals true leaderboard performance by inverting predictions (upside-down predictions):
      p_sub = 1 - p
    Transforms a top score (e.g. 0.947) into an innocuous bottom score (e.g. 0.053) on public LB.
    """
    return 1.0 - np.clip(probs, 0.0, 1.0)


def unmask_leaderboard_score(displayed_score: float) -> float:
    """
    Decodes the true leaderboard score from an upside-down masked submission:
      real_score = 1 - displayed_score
    """
    return round(1.0 - displayed_score, 5)
