"""
scaffold_runner.py — Fixed Execution Scaffold for Kaggle S6E11 Experiments.
=============================================================================
Fixed code (never agent-written) that:
  1. Loads train.csv reliably from the whitelisted data directory.
  2. Loads folds.json, safely extracting fold assignments while ignoring metadata keys (e.g. 'scheme', 'n_splits').
  3. Verifies every train.csv row has exactly one fold ID aligned to the row index.
  4. Calls the Engineer's `train_predict(X_train, y_train, X_val, y_val)` function for each fold.
  5. Validates predicted probabilities (shape, bounds in [0.0, 1.0], no NaNs).
  6. Writes out-of-fold predictions to `oof_predictions.parquet` in the format required by the evaluator harness.
"""

import os
import sys
import json
import logging
from pathlib import Path
import numpy as np
import pandas as pd

logger = logging.getLogger("Kaggle2.Scaffold")


def run_experiment_scaffold(
    run_dir: Path,
    data_dir: Path,
    folds_file: Path,
    model_module_path: Path
) -> None:
    """Executes the 5-fold cross-validation loop over the Engineer's train_predict function."""
    run_dir = Path(run_dir)
    data_dir = Path(data_dir)
    folds_file = Path(folds_file)
    model_module_path = Path(model_module_path)

    # 1. Locate train.csv
    train_path = data_dir / "train.csv"
    if not train_path.is_file():
        # Fallback to local run relative or environment
        alt_path = Path("/home/kizamladjanijebac/Desktop/discord-openclaw/artifacts/kaggle/s6e11/data/train.csv")
        if alt_path.is_file():
            train_path = alt_path
        else:
            raise FileNotFoundError(f"train.csv not found at {train_path} or {alt_path}")

    print(f"[Scaffold] Loading ground truth dataset from {train_path}...")
    df = pd.read_csv(train_path)
    total_rows = len(df)
    print(f"[Scaffold] Loaded {total_rows} rows.")

    # 2. Locate and safely parse folds.json
    if not folds_file.is_file():
        alt_folds = run_dir / "folds.json"
        if alt_folds.is_file():
            folds_file = alt_folds
        else:
            raise FileNotFoundError(f"folds.json not found at {folds_file} or {alt_folds}")

    print(f"[Scaffold] Loading frozen fold assignments from {folds_file}...")
    with open(folds_file, "r", encoding="utf-8") as f:
        raw_folds = json.load(f)

    # Safely extract fold assignments, strictly ignoring metadata keys like 'scheme', 'n_splits', etc.
    if "fold_assignments" in raw_folds:
        assignments_dict = raw_folds["fold_assignments"]
    elif "assignments" in raw_folds:
        assignments_dict = raw_folds["assignments"]
    else:
        # Filter for numeric string keys only
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

    # 3. Import Engineer's train_predict function
    if not model_module_path.is_file():
        raise FileNotFoundError(f"Model module not found at {model_module_path}")

    import importlib.util
    spec = importlib.util.spec_from_file_location("model_part", str(model_module_path))
    model_module = importlib.util.module_from_spec(spec)
    sys.modules["model_part"] = model_module
    spec.loader.exec_module(model_module)

    if not hasattr(model_module, "train_predict"):
        raise AttributeError(f"Model module {model_module_path} must define 'train_predict(X_train, y_train, X_val, y_val)'")

    train_predict_fn = getattr(model_module, "train_predict")

    # 4. 5-Fold Cross Validation Loop
    oof_predictions = np.zeros(total_rows, dtype=np.float32)
    feature_cols = [c for c in df.columns if c not in ("id", "is_fraud")]

    print(f"[Scaffold] Executing 5-fold CV with {len(feature_cols)} features...")
    for fold_idx in unique_folds:
        val_mask = (assigned_folds == fold_idx)
        tr_mask = ~val_mask

        X_tr = df.loc[tr_mask, feature_cols].copy()
        y_tr = df.loc[tr_mask, "is_fraud"].copy()
        X_val = df.loc[val_mask, feature_cols].copy()
        y_val = df.loc[val_mask, "is_fraud"].copy()

        print(f"[Scaffold] Training fold {fold_idx}: train={len(X_tr)}, val={len(X_val)}...")
        fold_preds = train_predict_fn(X_tr, y_tr, X_val, y_val)

        # Validate fold predictions
        fold_preds_arr = np.asarray(fold_preds, dtype=np.float64).flatten()
        expected_len = int(val_mask.sum())
        if len(fold_preds_arr) != expected_len:
            raise ValueError(
                f"ModelShapeError: fold {fold_idx} returned {len(fold_preds_arr)} predictions, expected {expected_len}"
            )

        if np.isnan(fold_preds_arr).any():
            raise ValueError(f"ModelOutputError: fold {fold_idx} predictions contain NaN values!")

        if (fold_preds_arr < 0.0).any() or (fold_preds_arr > 1.0).any():
            raise ValueError(f"ModelOutputError: fold {fold_idx} predictions outside probability range [0.0, 1.0]!")

        oof_predictions[val_mask] = fold_preds_arr

    # 5. Save oof_predictions.parquet
    out_parquet = run_dir / "oof_predictions.parquet"
    oof_df = pd.DataFrame({
        "id": id_arr,
        "pred": oof_predictions,
        "fold": assigned_folds
    })
    oof_df.to_parquet(out_parquet, index=False)
    print(f"[Scaffold] Successfully generated {out_parquet} ({len(oof_df)} rows).")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Kaggle S6E11 Experiment Scaffold Runner")
    parser.add_argument("--run-dir", required=True, type=str)
    parser.add_argument("--data-dir", required=True, type=str)
    parser.add_argument("--folds-file", required=True, type=str)
    parser.add_argument("--model-module", required=True, type=str)

    args = parser.parse_args()
    run_experiment_scaffold(
        run_dir=Path(args.run_dir),
        data_dir=Path(args.data_dir),
        folds_file=Path(args.folds_file),
        model_module_path=Path(args.model_module)
    )
