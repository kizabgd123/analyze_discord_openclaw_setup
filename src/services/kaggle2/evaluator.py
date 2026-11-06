"""
evaluator.py — Fixed Out-Of-Fold (OOF) Score Integrity & Leakage Verification Harness.
=====================================================================================
Fixed code running OUTSIDE the Firejail sandbox.
Validates agent out-of-fold prediction artifacts and calculates ground-truth ROC AUC:
  1. Checks existence of oof_predictions.parquet or oof_predictions.csv.
  2. Verifies presence and uniqueness of IDs matching ground truth train.csv.
  3. Verifies absence of NaNs / nulls and strictly bounds probabilities in [0.0, 1.0].
  4. Enforces fold isolation by cross-referencing per-row fold assignments against the
     Skeptic's frozen StratifiedKFold split (folds.json). Rejects predictions if fold
     ids are missing, altered, or trained across fold boundaries.
  5. Computes overall and per-fold ROC AUC deterministically with sklearn.
  6. Standard output from the agent script is completely ignored for metric evaluation.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger("Kaggle2.Evaluator")


def freeze_folds(
    train_path: Path,
    output_path: Path,
    n_splits: int = 5,
    random_state: int = 42,
    target_col: str = "is_fraud",
    id_col: str = "id"
) -> Dict[str, Any]:
    """
    Skeptic utility: Computes and freezes StratifiedKFold splits once per run.
    Stores explicit row-by-row assignments in JSON.
    """
    import pandas as pd
    from sklearn.model_selection import StratifiedKFold

    train_path = Path(train_path)
    output_path = Path(output_path)
    if not train_path.is_file():
        raise FileNotFoundError(f"train.csv not found at {train_path}")

    df = pd.read_csv(train_path, usecols=[id_col, target_col])
    id_arr = df[id_col].to_numpy()
    target_arr = df[target_col].to_numpy()
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)

    fold_assignments = {}
    for fold_idx, (_, val_idx) in enumerate(skf.split(df, target_arr)):
        val_ids = id_arr[val_idx]
        for s_id in val_ids:
            fold_assignments[str(int(s_id))] = int(fold_idx)

    payload = {
        "scheme": "StratifiedKFold",
        "n_splits": n_splits,
        "random_state": random_state,
        "target_col": target_col,
        "id_col": id_col,
        "total_samples": len(df),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fold_assignments_count": len(fold_assignments),
        "fold_assignments": fold_assignments
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    return payload


def evaluate_oof_predictions(
    run_dir: Path,
    data_dir: Path,
    folds_file: Optional[Path] = None,
    target_col: str = "is_fraud",
    id_col: str = "id"
) -> Dict[str, Any]:
    """
    Fixed evaluation harness: validates OOF artifact and computes verified ROC AUC.
    """
    import pandas as pd
    from sklearn.metrics import roc_auc_score

    run_dir = Path(run_dir)
    data_dir = Path(data_dir)

    # 1. Locate OOF predictions artifact
    oof_parquet = run_dir / "oof_predictions.parquet"
    oof_csv = run_dir / "oof_predictions.csv"

    if oof_parquet.is_file():
        oof_path = oof_parquet
        try:
            oof_df = pd.read_parquet(oof_path)
        except Exception as e:
            return {
                "status": "FAILED",
                "cv_score": None,
                "fold_scores": {},
                "total_samples": 0,
                "error": f"ScoreIntegrityError: Failed parsing oof_predictions.parquet: {e}"
            }
    elif oof_csv.is_file():
        oof_path = oof_csv
        try:
            oof_df = pd.read_csv(oof_path)
        except Exception as e:
            return {
                "status": "FAILED",
                "cv_score": None,
                "fold_scores": {},
                "total_samples": 0,
                "error": f"ScoreIntegrityError: Failed parsing oof_predictions.csv: {e}"
            }
    else:
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": 0,
            "error": "ScoreIntegrityError: Missing out-of-fold predictions file (oof_predictions.parquet or oof_predictions.csv) in run folder"
        }

    # 2. Locate frozen folds file
    if folds_file and Path(folds_file).is_file():
        f_path = Path(folds_file)
    elif (run_dir / "folds.json").is_file():
        f_path = run_dir / "folds.json"
    elif (data_dir.parent / "folds.json").is_file():
        f_path = data_dir.parent / "folds.json"
    else:
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": 0,
            "error": "ScoreIntegrityError: Frozen fold assignment file (folds.json) not found. Skeptic freeze required."
        }

    try:
        with open(f_path, "r", encoding="utf-8") as f:
            folds_data = json.load(f)
        frozen_assignments = folds_data.get("fold_assignments", {})
    except Exception as e:
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": 0,
            "error": f"ScoreIntegrityError: Failed loading frozen folds from {f_path}: {e}"
        }

    # 3. Locate ground truth train.csv
    train_path = data_dir / "train.csv"
    if not train_path.is_file():
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": 0,
            "error": f"ScoreIntegrityError: Ground truth train.csv not found at {train_path}"
        }

    try:
        train_df = pd.read_csv(train_path, usecols=[id_col, target_col])
    except Exception as e:
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": 0,
            "error": f"ScoreIntegrityError: Failed loading ground truth labels: {e}"
        }

    # 4. Standardize and validate columns
    col_map = {col.lower(): col for col in oof_df.columns}

    # Check ID column
    actual_id_col = None
    for cand in [id_col.lower(), "id", "sample_id"]:
        if cand in col_map:
            actual_id_col = col_map[cand]
            break
    if not actual_id_col:
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": 0,
            "error": f"ScoreIntegrityError: OOF predictions missing required ID column '{id_col}'"
        }

    # Check Prediction column
    actual_pred_col = None
    for cand in ["pred", "prediction", "pred_proba", target_col.lower(), "probability"]:
        if cand in col_map and col_map[cand] != actual_id_col:
            actual_pred_col = col_map[cand]
            break
    if not actual_pred_col:
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": 0,
            "error": "ScoreIntegrityError: OOF predictions missing probability prediction column (e.g. 'pred', 'prediction', 'is_fraud')"
        }

    # Check Fold column (Deliverable 4 Leakage Check)
    actual_fold_col = None
    for cand in ["fold", "fold_id", "fold_idx", "split"]:
        if cand in col_map:
            actual_fold_col = col_map[cand]
            break
    if not actual_fold_col:
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": 0,
            "error": "LeakageIntegrityError: OOF predictions missing required 'fold' column to verify fold isolation"
        }

    # 5. Row Count & ID Uniqueness Validation
    if len(oof_df) != len(train_df):
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": len(oof_df),
            "error": f"ScoreIntegrityError: Row count mismatch: expected {len(train_df)} rows, found {len(oof_df)}"
        }

    if oof_df[actual_id_col].duplicated().any():
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": len(oof_df),
            "error": "ScoreIntegrityError: OOF predictions contain duplicate IDs"
        }

    # ID set alignment
    oof_ids = set(oof_df[actual_id_col].astype(int))
    train_ids = set(train_df[id_col].astype(int))
    if oof_ids != train_ids:
        missing = len(train_ids - oof_ids)
        extra = len(oof_ids - train_ids)
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": len(oof_df),
            "error": f"ScoreIntegrityError: ID mismatch with ground truth (missing {missing}, unexpected {extra})"
        }

    # 6. NaN / Null & Probability Range Checks
    if oof_df[[actual_id_col, actual_pred_col, actual_fold_col]].isna().any().any():
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": len(oof_df),
            "error": "ScoreIntegrityError: OOF predictions contain NaN or null values"
        }

    # Convert predictions to float and check range [0.0, 1.0]
    try:
        oof_df[actual_pred_col] = oof_df[actual_pred_col].astype(float)
    except Exception as e:
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": len(oof_df),
            "error": f"ScoreIntegrityError: Prediction values cannot be parsed as float: {e}"
        }

    if (oof_df[actual_pred_col] < 0.0).any() or (oof_df[actual_pred_col] > 1.0).any():
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": len(oof_df),
            "error": "ScoreIntegrityError: Prediction probabilities outside valid [0.0, 1.0] range"
        }

    # 7. Deliverable 4: Leakage check against frozen fold assignments
    # Ensure each prediction's fold matches the Skeptic's frozen assignment
    mismatches = 0
    oof_id_series = oof_df[actual_id_col].astype(str)
    oof_fold_series = oof_df[actual_fold_col].astype(int)

    # Fast vector verification
    for s_id, s_fold in zip(oof_id_series, oof_fold_series):
        expected_fold = frozen_assignments.get(s_id)
        if expected_fold is None or int(expected_fold) != s_fold:
            mismatches += 1
            if mismatches > 10:
                break

    if mismatches > 0:
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": len(oof_df),
            "error": (
                f"LeakageIntegrityError: Fold assignment mismatch detected ({mismatches}+ rows failed fold alignment "
                f"against frozen CV split). Agent code must predict strictly out-of-fold matching frozen fold assignments."
            )
        }

    # 8. Compute Ground-Truth ROC AUC Metrics
    truth_map = dict(zip(train_df[id_col].astype(int), train_df[target_col].astype(int)))
    y_true = oof_df[actual_id_col].astype(int).map(truth_map)
    y_pred = oof_df[actual_pred_col]

    try:
        overall_auc = float(roc_auc_score(y_true, y_pred))
    except Exception as e:
        return {
            "status": "FAILED",
            "cv_score": None,
            "fold_scores": {},
            "total_samples": len(oof_df),
            "error": f"ScoreIntegrityError: Calculation of overall ROC AUC failed: {e}"
        }

    # Per-fold ROC AUC
    fold_scores = {}
    for f_id in sorted(oof_fold_series.unique()):
        mask = (oof_fold_series == f_id)
        try:
            f_auc = float(roc_auc_score(y_true[mask], y_pred[mask]))
            fold_scores[str(f_id)] = round(f_auc, 5)
        except Exception as e:
            fold_scores[str(f_id)] = None

    return {
        "status": "PASSED",
        "cv_score": round(overall_auc, 5),
        "fold_scores": fold_scores,
        "total_samples": len(oof_df),
        "error": None
    }


def main():
    parser = argparse.ArgumentParser(description="Kaggle2 Fixed OOF Evaluator Harness")
    subparsers = parser.add_subparsers(dest="action", required=True)

    # Freeze folds
    freeze_parser = subparsers.add_parser("freeze")
    freeze_parser.add_argument("--train-path", required=True, type=str)
    freeze_parser.add_argument("--out-path", required=True, type=str)
    freeze_parser.add_argument("--n-splits", default=5, type=int)
    freeze_parser.add_argument("--random-state", default=42, type=int)

    # Evaluate OOF
    eval_parser = subparsers.add_parser("evaluate")
    eval_parser.add_argument("--run-dir", required=True, type=str)
    eval_parser.add_argument("--data-dir", required=True, type=str)
    eval_parser.add_argument("--folds-file", default=None, type=str)

    args = parser.parse_args()

    if args.action == "freeze":
        res = freeze_folds(
            train_path=Path(args.train_path),
            output_path=Path(args.out_path),
            n_splits=args.n_splits,
            random_state=args.random_state
        )
        print(json.dumps({"status": "SUCCESS", "total_samples": res["total_samples"], "out_path": args.out_path}))
    elif args.action == "evaluate":
        res = evaluate_oof_predictions(
            run_dir=Path(args.run_dir),
            data_dir=Path(args.data_dir),
            folds_file=Path(args.folds_file) if args.folds_file else None
        )
        print(json.dumps(res))


if __name__ == "__main__":
    main()
