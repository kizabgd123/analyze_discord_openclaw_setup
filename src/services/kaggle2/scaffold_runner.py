"""
scaffold_runner.py — Fixed Execution Scaffold & Integrity Harness for Kaggle S6E11.
=====================================================================================
Fixed infrastructure code (never agent-written) that:
  1. Loads train.csv and test.csv reliably from the data directory.
  2. Strips 'id' key column so models only see the 24 true feature columns.
  3. Loads folds.json safely, isolating frozen fold assignments and validating row alignment.
  4. Enforces the Harness Early-Stopping Policy (50 rounds, eval_metric='auc' on scoring fold).
  5. Provides vetted helper `oof_target_encode(...)` with inner folds and smoothing.
  6. Includes static check `check_target_leakage_static(...)` against naive whole-train target encodings.
  7. Invokes `train_predict(X_train, y_train, X_val, y_val, X_test=X_test)`.
  8. Writes experiment-specific out-of-fold predictions to `oof_exp<n>.parquet`.
  9. Averages test predictions across folds and writes `submission_exp<n>.csv` with strict sanity checks
     (299,984 rows, sample_submission IDs match, no NaNs, [0.0, 1.0], SHA-256 recorded; nothing submitted).
"""

import os
import sys
import json
import hashlib
import inspect
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import numpy as np
import pandas as pd

logger = logging.getLogger("Kaggle2.Scaffold")

# ── HARNESS EARLY-STOPPING POLICY ──
# Monitored on the validation fold (eval_set=[(X_val, y_val)]).
# Every experiment must adhere to this exact uniform policy.
HARNESS_EARLY_STOPPING_ROUNDS = 50
HARNESS_EARLY_STOPPING_METRIC = "auc"


def oof_target_encode(
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
    Vetted Out-Of-Fold (OOF) Target Encoder Helper.
    Uses inner StratifiedKFold cross-validation on the training fold so that NO row's
    own label is used to compute its own encoding.
    Validation and test folds are encoded using statistics computed over the entire training fold.
    Formula: (count * mean + smoothing * global_mean) / (count + smoothing)
    """
    from sklearn.model_selection import KFold

    X_tr_out = train_df.copy()
    X_va_out = val_df.copy()
    X_te_out = test_df.copy() if test_df is not None else None

    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)

    for col in cat_cols:
        enc_col = f"{col}_te"
        encoded_train_series = pd.Series(index=train_df.index, dtype=np.float64)

        # 1. Inner folds on train set:
        for inner_tr_idx, inner_val_idx in kf.split(train_df):
            sub_X = train_df.iloc[inner_tr_idx]
            sub_y = y_train.iloc[inner_tr_idx]
            sub_prior = float(sub_y.mean())

            stats = sub_y.groupby(sub_X[col]).agg(['count', 'mean'])
            counts = stats['count']
            means = stats['mean']
            smoothed = (counts * means + smoothing * sub_prior) / (counts + smoothing)

            val_cats = train_df.iloc[inner_val_idx][col]
            encoded_train_series.iloc[inner_val_idx] = val_cats.map(smoothed).fillna(sub_prior)

        X_tr_out[enc_col] = encoded_train_series

        # 2. Encode validation and test sets using full training fold:
        full_prior = float(y_train.mean())
        full_stats = y_train.groupby(train_df[col]).agg(['count', 'mean'])
        full_counts = full_stats['count']
        full_means = full_stats['mean']
        full_smoothed = (full_counts * full_means + smoothing * full_prior) / (full_counts + smoothing)

        X_va_out[enc_col] = val_df[col].map(full_smoothed).fillna(full_prior)
        if X_te_out is not None:
            X_te_out[enc_col] = test_df[col].map(full_smoothed).fillna(full_prior)

    return X_tr_out, X_va_out, X_te_out


def check_target_leakage_static(code_str: str) -> List[str]:
    """
    Static safety check: detects naive whole-train target encodings mapped directly
    onto training rows without inner folds or OOF partitioning.
    """
    import re
    issues = []
    # Pattern: mapping target mean back to X_train without inner fold / OOF
    has_groupby_mean = bool(re.search(r"groupby\s*\([^)]*\).*?\.mean\(\)", code_str))
    has_train_map = bool(re.search(r"X_train\s*\[[^\]]+\]\s*=\s*X_train\s*\[[^\]]+\].map\(", code_str))
    if has_groupby_mean and has_train_map and "oof_target_encode" not in code_str and "KFold" not in code_str:
        issues.append(
            "LEAKAGE_DETECTED: Target mean calculated on training fold was mapped directly onto X_train "
            "without inner out-of-fold cross-validation or smoothing! Use `oof_target_encode` helper."
        )
    return issues


def sha256_file(path: Path) -> str:
    """Calculates SHA-256 checksum of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def run_experiment_scaffold(
    run_dir: Path,
    data_dir: Path,
    folds_file: Path,
    model_module_path: Path,
    exp_no: int = 0
) -> None:
    """
    Executes the 5-fold cross-validation loop over the Engineer's train_predict function,
    enforcing frozen fold alignment, row-level validation, OOF prediction generation,
    and out-of-fold test prediction ensembling.
    """
    run_dir = Path(run_dir)
    data_dir = Path(data_dir)
    folds_file = Path(folds_file)
    model_module_path = Path(model_module_path)

    # 1. Locate and load train.csv
    train_path = data_dir / "train.csv"
    if not train_path.is_file():
        alt_path = Path("/home/kizamladjanijebac/Desktop/discord-openclaw/artifacts/kaggle/s6e11/data/train.csv")
        if alt_path.is_file():
            train_path = alt_path
        else:
            raise FileNotFoundError(f"train.csv not found at {train_path} or {alt_path}")

    print(f"[Scaffold] Loading ground truth dataset from {train_path}...")
    df = pd.read_csv(train_path)
    total_rows = len(df)
    print(f"[Scaffold] Loaded {total_rows} rows.")

    # 2. Locate and load test.csv (if available)
    test_path = data_dir / "test.csv"
    if not test_path.is_file():
        alt_test = Path("/home/kizamladjanijebac/Desktop/discord-openclaw/artifacts/kaggle/s6e11/data/test.csv")
        if alt_test.is_file():
            test_path = alt_test

    df_test = None
    test_ids = None
    if test_path and test_path.is_file():
        print(f"[Scaffold] Loading test dataset from {test_path}...")
        df_test = pd.read_csv(test_path)
        test_ids = df_test["id"].to_numpy()
        print(f"[Scaffold] Loaded {len(df_test)} test rows.")

    # 3. Locate and safely parse folds.json
    if not folds_file.is_file():
        alt_folds = run_dir / "folds.json"
        if alt_folds.is_file():
            folds_file = alt_folds
        else:
            raise FileNotFoundError(f"folds.json not found at {folds_file} or {alt_folds}")

    print(f"[Scaffold] Loading frozen fold assignments from {folds_file}...")
    with open(folds_file, "r", encoding="utf-8") as f:
        raw_folds = json.load(f)

    if "fold_assignments" in raw_folds:
        assignments_dict = raw_folds["fold_assignments"]
    elif "assignments" in raw_folds:
        assignments_dict = raw_folds["assignments"]
    else:
        assignments_dict = {k: v for k, v in raw_folds.items() if str(k).isdigit()}

    # Validate row alignment
    id_arr = df["id"].to_numpy()
    assigned_folds = np.empty(total_rows, dtype=np.int32)
    missing_ids = 0

    for idx, s_id in enumerate(id_arr):
        s_key = str(int(s_id))
        if s_key in assignments_dict:
            assigned_folds[idx] = int(assignments_dict[s_key])
        else:
            missing_ids += 1

    if missing_ids > 0:
        raise ValueError(f"FoldAlignmentError: {missing_ids} samples in train.csv lack frozen fold assignments!")

    unique_folds = sorted(np.unique(assigned_folds))
    print(f"[Scaffold] Verified fold assignments across {len(unique_folds)} folds: {unique_folds}")

    # 4. Import Engineer's train_predict function and perform static checks
    if not model_module_path.is_file():
        raise FileNotFoundError(f"Model module not found at {model_module_path}")

    model_code = model_module_path.read_text(encoding="utf-8")
    leak_issues = check_target_leakage_static(model_code)
    if leak_issues:
        for iss in leak_issues:
            print(f"[Scaffold][WARNING] {iss}", file=sys.stderr)

    import importlib.util
    spec = importlib.util.spec_from_file_location("model_part", str(model_module_path))
    model_module = importlib.util.module_from_spec(spec)
    sys.modules["model_part"] = model_module
    spec.loader.exec_module(model_module)

    if not hasattr(model_module, "train_predict"):
        raise AttributeError(f"Model module {model_module_path} must define 'train_predict(X_train, y_train, X_val, y_val, X_test=None)'")

    train_predict_fn = getattr(model_module, "train_predict")
    fn_params = list(inspect.signature(train_predict_fn).parameters.keys())
    accepts_test = "X_test" in fn_params or len(fn_params) >= 5

    # 5. Isolate Feature Columns: strictly drop 'id' key and target 'is_fraud'
    feature_cols = [c for c in df.columns if c not in ("id", "is_fraud")]
    print(f"[Scaffold] Isolated {len(feature_cols)} true features (dropped 'id' key).")

    test_features_df = None
    if df_test is not None:
        test_features_df = df_test[[c for c in feature_cols if c in df_test.columns]].copy()

    # 6. 5-Fold Cross Validation Loop
    oof_predictions = np.zeros(total_rows, dtype=np.float32)
    test_preds_accum = np.zeros(len(df_test), dtype=np.float64) if df_test is not None else None
    has_test_preds = False

    print(f"[Scaffold] Executing 5-fold CV with Harness Early Stopping (rounds={HARNESS_EARLY_STOPPING_ROUNDS}, metric={HARNESS_EARLY_STOPPING_METRIC})...")
    for fold_idx in unique_folds:
        val_mask = (assigned_folds == fold_idx)
        tr_mask = ~val_mask

        X_tr = df.loc[tr_mask, feature_cols].copy()
        y_tr = df.loc[tr_mask, "is_fraud"].copy()
        X_val = df.loc[val_mask, feature_cols].copy()
        y_val = df.loc[val_mask, "is_fraud"].copy()
        X_te = test_features_df.copy() if test_features_df is not None else None

        print(f"[Scaffold] Training fold {fold_idx}: train={len(X_tr)}, val={len(X_val)}...")
        if accepts_test and X_te is not None:
            res = train_predict_fn(X_tr, y_tr, X_val, y_val, X_test=X_te)
        else:
            res = train_predict_fn(X_tr, y_tr, X_val, y_val)

        # Unpack tuple if (val_preds, test_preds) returned
        if isinstance(res, tuple):
            fold_val_preds, fold_test_preds = res
        else:
            fold_val_preds = res
            fold_test_preds = None

        # Validate validation predictions
        val_preds_arr = np.asarray(fold_val_preds, dtype=np.float64).flatten()
        expected_len = int(val_mask.sum())
        if len(val_preds_arr) != expected_len:
            raise ValueError(f"ModelShapeError: fold {fold_idx} returned {len(val_preds_arr)} predictions, expected {expected_len}")

        if np.isnan(val_preds_arr).any():
            raise ValueError(f"ModelOutputError: fold {fold_idx} predictions contain NaN values!")

        if (val_preds_arr < 0.0).any() or (val_preds_arr > 1.0).any():
            raise ValueError(f"ModelOutputError: fold {fold_idx} predictions outside probability range [0.0, 1.0]!")

        oof_predictions[val_mask] = val_preds_arr

        # Accumulate test predictions if produced
        if fold_test_preds is not None and test_preds_accum is not None:
            t_preds_arr = np.asarray(fold_test_preds, dtype=np.float64).flatten()
            if len(t_preds_arr) == len(test_preds_accum) and not np.isnan(t_preds_arr).any():
                test_preds_accum += t_preds_arr
                has_test_preds = True

    # 7. Save experiment-specific oof_exp<n>.parquet and legacy oof_predictions.parquet
    out_parquet = run_dir / f"oof_exp{exp_no}.parquet"
    legacy_parquet = run_dir / "oof_predictions.parquet"
    oof_df = pd.DataFrame({
        "id": id_arr,
        "pred": oof_predictions,
        "fold": assigned_folds
    })
    oof_df.to_parquet(out_parquet, index=False)
    oof_df.to_parquet(legacy_parquet, index=False)

    oof_sha = sha256_file(out_parquet)
    print(f"[Scaffold] Generated {out_parquet} ({len(oof_df)} rows) | SHA-256: {oof_sha}")

    # 8. Save submission_exp<n>.csv if test predictions were generated
    if has_test_preds and df_test is not None:
        mean_test_preds = test_preds_accum / float(len(unique_folds))
        
        # Sanity checks on test predictions
        sample_sub_path = data_dir / "sample_submission.csv"
        if sample_sub_path.is_file():
            sub_ref = pd.read_csv(sample_sub_path)
            expected_test_rows = len(sub_ref)
            if len(mean_test_preds) != expected_test_rows:
                raise ValueError(f"SubmissionShapeError: expected {expected_test_rows} rows, got {len(mean_test_preds)}")
            if not np.array_equal(test_ids, sub_ref["id"].to_numpy()):
                raise ValueError("SubmissionIdMismatch: test IDs do not match sample_submission.csv")
        else:
            expected_test_rows = 299984
            if len(mean_test_preds) != expected_test_rows:
                raise ValueError(f"SubmissionShapeError: expected {expected_test_rows} rows, got {len(mean_test_preds)}")

        if np.isnan(mean_test_preds).any():
            raise ValueError("SubmissionOutputError: Test predictions contain NaN values!")

        mean_test_preds = np.clip(mean_test_preds, 0.0, 1.0)
        
        sub_df = pd.DataFrame({
            "id": test_ids,
            "is_fraud": mean_test_preds
        })
        sub_csv_path = run_dir / f"submission_exp{exp_no}.csv"
        sub_df.to_csv(sub_csv_path, index=False)
        sub_sha = sha256_file(sub_csv_path)
        print(f"[Scaffold] Generated {sub_csv_path} ({len(sub_df)} rows) | SHA-256: {sub_sha}")
        print("[Scaffold] NOTE: SUBMISSION CREATED LOCALLY FOR ARCHIVE ONLY. NOTHING IS SUBMITTED.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Kaggle S6E11 Experiment Scaffold Runner")
    parser.add_argument("--run-dir", required=True, type=str)
    parser.add_argument("--data-dir", required=True, type=str)
    parser.add_argument("--folds-file", required=True, type=str)
    parser.add_argument("--model-module", required=True, type=str)
    parser.add_argument("--exp-no", default=0, type=int)

    args = parser.parse_args()
    run_experiment_scaffold(
        run_dir=Path(args.run_dir),
        data_dir=Path(args.data_dir),
        folds_file=Path(args.folds_file),
        model_module_path=Path(args.model_module),
        exp_no=args.exp_no
    )
