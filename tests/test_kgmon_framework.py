"""
test_kgmon_framework.py — Verification Suite for KGMON Strategic Framework
===========================================================================
Validates:
  1. Snap features (nearest value recovery & diff perturbation calculation).
  2. Decimal and digit extraction (frac, d1, d2, frac100, mod10, mod100, is_round, denominator residuals).
  3. Benford's Law deviation calculation.
  4. String TF-IDF character n-grams over continuous columns.
  5. cKDTree Nearest Neighbor Ground Truth Anchor extraction.
  6. Manifold projections (PCA & Gaussian Random Projection fitted strictly on original data).
  7. Strict leak-free nested target encoding.
  8. Logit Meta-Learner (to_logit, from_logit, L2 regularization).
  9. Diversity filter (correlation < 0.99 enforcement).
 10. 4-Level Stacker registration & end-to-end fitting.
 11. Fast 1-feature CPU screening.
 12. Upside-down submission score masking & unmasking.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from src.services.kaggle2.feature_engine import KGMONFeatureEngine
from src.services.kaggle2.stacking_engine import (
    to_logit,
    from_logit,
    DiversityFilter,
    LogitMetaLearner,
    FourLevelStacker
)
from src.services.kaggle2.screening_and_masking import (
    fast_1feature_cpu_screening,
    mask_submission_predictions,
    unmask_leaderboard_score
)


def test_1_snap_features():
    orig_df = pd.DataFrame({"MonthlyCharges": [29.85, 56.95, 53.85, 42.30, 70.70]})
    # Synthetic samples with slight generator perturbation noise
    synth_df = pd.DataFrame({"MonthlyCharges": [29.87, 56.90, 70.75]})

    snap_df = KGMONFeatureEngine.extract_snap_features(synth_df, orig_df, ["MonthlyCharges"])
    assert "MonthlyCharges_snap" in snap_df.columns
    assert "MonthlyCharges_snap_diff" in snap_df.columns

    # Verify nearest value recovery
    assert pytest.approx(snap_df["MonthlyCharges_snap"].iloc[0], 0.01) == 29.85
    assert pytest.approx(snap_df["MonthlyCharges_snap_diff"].iloc[0], 0.001) == 0.02
    assert pytest.approx(snap_df["MonthlyCharges_snap"].iloc[2], 0.01) == 70.70


def test_2_decimal_digit_features():
    df = pd.DataFrame({"amount_usd": [123.456, 10.000, 99.500]})
    digit_df = KGMONFeatureEngine.extract_decimal_digit_features(df, ["amount_usd"])

    # Row 0: 123.456
    # frac ≈ 0.456, d1 = 4, d2 = 5, frac100 = 46, mod10 = 3, mod100 = 23, is_round = 0
    assert digit_df["amount_usd_d1"].iloc[0] == 4
    assert digit_df["amount_usd_d2"].iloc[0] == 5
    assert digit_df["amount_usd_frac100"].iloc[0] == 46
    assert digit_df["amount_usd_mod10"].iloc[0] == 3
    assert digit_df["amount_usd_mod100"].iloc[0] == 23
    assert digit_df["amount_usd_is_round"].iloc[0] == 0

    # Row 1: 10.000 -> is_round must be 1
    assert digit_df["amount_usd_is_round"].iloc[1] == 1
    assert digit_df["amount_usd_res_half"].iloc[1] == 0.0

    # Row 2: 99.500 -> res_half must be 0.0
    assert pytest.approx(digit_df["amount_usd_res_half"].iloc[2], 0.0001) == 0.0
    assert digit_df["amount_usd_d1_d2"].iloc[0] == "4_5"


def test_3_benford_law_deviation():
    # Natural log-uniform numbers should follow Benford's Law closely (low deviation)
    np.random.seed(42)
    benford_sample = pd.Series(10.0 ** np.random.uniform(1, 6, 5000))
    dev_natural = KGMONFeatureEngine.compute_benford_deviation(benford_sample)

    # Uniform sample in [100, 200] where leading digit is always 1 (high deviation)
    unnatural_sample = pd.Series(np.random.uniform(100, 199, 5000))
    dev_unnatural = KGMONFeatureEngine.compute_benford_deviation(unnatural_sample)

    assert dev_natural < dev_unnatural
    assert dev_natural < 0.10
    assert dev_unnatural > 0.30


def test_4_string_tfidf_features():
    train_s = pd.Series([12.345, 12.345, 99.888, 45.123])
    test_s = pd.Series([12.345, 55.555])

    tr_tfidf, te_tfidf = KGMONFeatureEngine.extract_string_tfidf_features(
        train_s, test_s, max_features=4, prefix="amt"
    )
    assert tr_tfidf.shape == (4, 4)
    assert te_tfidf.shape == (2, 4)
    assert not tr_tfidf.isna().any().any()


def test_5_ckdtree_anchor_and_manifold():
    orig_df = pd.DataFrame({
        "feat1": [1.0, 2.0, 3.0, 4.0, 5.0],
        "feat2": [10.0, 20.0, 30.0, 40.0, 50.0],
        "is_fraud": [0, 0, 1, 1, 0]
    })
    synth_df = pd.DataFrame({
        "feat1": [1.05, 3.10],
        "feat2": [10.2, 29.8]
    })

    # 1. cKDTree anchor
    anchor_df = KGMONFeatureEngine.extract_ckdtree_anchor_features(
        synth_df, orig_df, ["feat1", "feat2"], target_col="is_fraud"
    )
    assert "orig_nn_dist" in anchor_df.columns
    assert "orig_target_anchor" in anchor_df.columns
    # synth row 0 (1.05, 10.2) is closest to orig row 0 (1.0, 10.0) -> target 0
    assert anchor_df["orig_target_anchor"].iloc[0] == 0
    # synth row 1 (3.10, 29.8) is closest to orig row 2 (3.0, 30.0) -> target 1
    assert anchor_df["orig_target_anchor"].iloc[1] == 1

    # 2. Manifold Projections
    tr_proj, te_proj = KGMONFeatureEngine.extract_manifold_projections(
        train_df=synth_df, orig_df=orig_df, feature_cols=["feat1", "feat2"], n_components=2
    )
    assert "pca_orig_0" in tr_proj.columns
    assert "grp_orig_0" in tr_proj.columns
    assert tr_proj.shape == (2, 4)


def test_6_nested_leak_free_target_encoding():
    np.random.seed(42)
    n = 100
    cats = np.random.choice(["A", "B", "C"], n)
    # Target correlated with categories
    target = pd.Series(np.where(cats == "A", 0.8, np.where(cats == "B", 0.2, 0.5)))
    train_df = pd.DataFrame({"cat": cats})
    val_df = pd.DataFrame({"cat": ["A", "B", "C"]})

    tr_enc, va_enc, _ = KGMONFeatureEngine.nested_target_encode(
        train_df=train_df,
        val_df=val_df,
        cat_cols=["cat"],
        y_train=target,
        n_splits=5,
        smoothing=5.0
    )

    assert "cat_te_mean" in tr_enc.columns
    assert "cat_te_mean" in va_enc.columns
    assert len(tr_enc) == 100
    assert not tr_enc["cat_te_mean"].isna().any()
    # In val, category A should have significantly higher encoded value than B
    assert va_enc["cat_te_mean"].iloc[0] > va_enc["cat_te_mean"].iloc[1]


def test_7_logit_meta_learner_and_stacking():
    np.random.seed(42)
    n = 200
    y_true = np.random.choice([0, 1], n, p=[0.7, 0.3])

    # Model 1: slightly good
    m1_oof = np.clip(y_true * 0.4 + 0.3 + np.random.normal(0, 0.2, n), 0.01, 0.99)
    # Model 2: orthogonal model with different noise
    m2_oof = np.clip(y_true * 0.35 + 0.3 + np.random.normal(0, 0.25, n), 0.01, 0.99)

    stacker = FourLevelStacker(run_dir="test_run")
    # Register Level 2 models
    ok1, _ = stacker.register_level2_model("xgb_model", m1_oof, y_true=y_true)
    ok2, _ = stacker.register_level2_model("lgb_model", m2_oof, y_true=y_true)
    assert ok1 and ok2

    # Register Level 3 intermediate model
    m3_oof = np.clip((m1_oof + m2_oof) / 2.0, 0.01, 0.99)
    stacker.register_level3_model("nn_meta_stk", m3_oof)

    fit_res = stacker.fit_final_stack(y_true)
    assert fit_res["n_models"] == 3
    assert fit_res["ensemble_auc"] > 0.70
    assert len(fit_res["model_weights"]) == 3


def test_8_diversity_filter():
    np.random.seed(42)
    n = 100
    y_true = np.random.choice([0, 1], n)
    oof1 = np.random.uniform(0.1, 0.9, n)

    df_filter = DiversityFilter(min_auc=0.50, max_correlation=0.99)
    # Clone model 1 with tiny jitter (correlation > 0.999)
    oof_clone = oof1 + np.random.normal(0, 1e-4, n)

    passed, reason, auc, corr = df_filter.evaluate_candidate(
        candidate_oof=oof_clone,
        candidate_name="clone_model",
        existing_oofs={"m1": oof1},
        y_true=y_true
    )
    assert not passed
    assert "exceeds diversity limit" in reason


def test_9_fast_1feature_cpu_screening():
    np.random.seed(42)
    n = 100
    y_true = np.random.choice([0, 1], n)
    base_oof = np.full(n, 0.5)

    # Strong signal feature
    good_feat = pd.Series(y_true * 2.0 + np.random.normal(0, 0.5, n))
    res_good = fast_1feature_cpu_screening(base_oof, y_true, good_feat)
    assert res_good["worth_gpu_full_train"] is True
    assert res_good["recommendation"] == "PROCEED"

    # Pure noise feature
    noise_feat = pd.Series(np.random.normal(0, 1.0, n))
    res_noise = fast_1feature_cpu_screening(base_oof, y_true, noise_feat)
    # Noise feature shouldn't produce high delta_cv
    assert res_noise["delta_cv"] <= res_good["delta_cv"]


def test_10_upside_down_score_masking():
    # 0.94705 AUC submission
    probs = np.array([0.9, 0.8, 0.2, 0.1])
    masked = mask_submission_predictions(probs)
    assert np.allclose(masked, [0.1, 0.2, 0.8, 0.9])

    # Unmask leaderboard score
    assert unmask_leaderboard_score(0.05295) == 0.94705
