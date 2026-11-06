#!/usr/bin/env python3
"""
scripts/run_step3_experiments.py — Execute Exp 0 Baseline and Exp 2 Reproduction in Sandboxed Runner.
===================================================================================================
Executes:
  1. Exp 0 (Infrastructure LightGBM baseline on 24 raw feature columns under uniform early-stopping policy).
  2. Exp 2 reproduction (exact script from run 050809 under the same frozen folds).
Evaluates both with the ground-truth harness outside the sandbox and calculates:
  - Overall ROC-AUC and per-fold ROC-AUCs
  - Wall-clock execution time
  - File SHA-256 hashes (script, OOF parquet, and submission CSV)
  - Paired comparison: d_i = auc_exp2_repro_i - auc_exp0_i and statistical verdict.
"""

import os
import sys
import json
import time
import shutil
import hashlib
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.kaggle2.runner import LocalRunner
from src.services.kaggle2.evaluator import compute_paired_verdict

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

DATA_DIR = PROJECT_ROOT / "artifacts" / "kaggle" / "s6e11" / "data"
FROZEN_FOLDS_PATH = PROJECT_ROOT / "artifacts" / "kaggle" / "s6e11" / "20261106_050809" / "folds.json"
SCAFFOLD_SRC = PROJECT_ROOT / "src" / "services" / "kaggle2" / "scaffold_runner.py"

EXP0_DIR = PROJECT_ROOT / "artifacts" / "kaggle" / "s6e11" / "exp0_baseline"
EXP2_DIR = PROJECT_ROOT / "artifacts" / "kaggle" / "s6e11" / "reproduce_050809_exp2"
ORIGINAL_EXP2_SCRIPT = PROJECT_ROOT / "artifacts" / "kaggle" / "s6e11" / "20261106_050809" / "model_part.py"

EXP0_CODE = '''import numpy as np
import pandas as pd
import lightgbm as lgb
from lightgbm import LGBMClassifier
from typing import Tuple, Optional

def train_predict(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    X_test: Optional[pd.DataFrame] = None
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """
    Exp 0: Infrastructure Reference Baseline on raw 24 feature columns.
    Enforces Harness Early-Stopping Policy: 50 rounds, eval_metric='auc' on validation fold.
    """
    X_train = X_train.copy()
    X_val = X_val.copy()
    X_test = X_test.copy() if X_test is not None else None

    # Cast categorical and boolean columns for native LightGBM handling
    cat_cols = X_train.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
    for col in cat_cols:
        X_train[col] = X_train[col].astype('category')
        X_val[col] = X_val[col].astype('category')
        if X_test is not None and col in X_test.columns:
            X_test[col] = X_test[col].astype('category')

    model = LGBMClassifier(
        n_estimators=1500,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=-1,
        min_child_samples=20,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbose=-1
    )

    # Harness early-stopping policy (50 rounds, eval_metric='auc')
    callbacks = [
        lgb.early_stopping(stopping_rounds=50, verbose=False),
        lgb.log_evaluation(period=0)
    ]

    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        eval_metric='auc',
        callbacks=callbacks
    )

    val_preds = model.predict_proba(X_val)[:, 1]
    test_preds = model.predict_proba(X_test)[:, 1] if X_test is not None else None

    return val_preds, test_preds
'''


async def run_exp0(runner: LocalRunner) -> dict:
    print("\n" + "=" * 80)
    print("▶ STARTING EXP 0: INFRASTRUCTURE RAW LIGHTGBM BASELINE")
    print("=" * 80)
    EXP0_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Setup files
    scaffold_dst = EXP0_DIR / "run_scaffold.py"
    shutil.copy2(SCAFFOLD_SRC, scaffold_dst)

    folds_dst = EXP0_DIR / "folds.json"
    if not folds_dst.is_file() or sha256_file(folds_dst) != sha256_file(FROZEN_FOLDS_PATH):
        shutil.copy2(FROZEN_FOLDS_PATH, folds_dst)

    model_dst = EXP0_DIR / "model_part_exp0.py"
    model_dst.write_text(EXP0_CODE, encoding="utf-8")
    script_sha = sha256_file(model_dst)
    print(f"Exp 0 model script written to {model_dst} | SHA-256: {script_sha}")

    # 2. Execute via LocalRunner inside Firejail
    start_time = time.time()
    oof_target = EXP0_DIR / "oof_exp0.parquet"
    cmd_args = [
        "--run-dir", str(EXP0_DIR),
        "--data-dir", str(DATA_DIR),
        "--folds-file", str(folds_dst),
        "--model-module", str(model_dst),
        "--exp-no", "0"
    ]
    print(f"Launching sandboxed execution via Firejail...")
    exec_res = await runner.execute_script(scaffold_dst, args=cmd_args, verify_oof=True, oof_file=oof_target)
    elapsed = time.time() - start_time
    print(f"Exp 0 finished in {elapsed:.2f}s | Exit code: {exec_res.get('exit_code')}")

    # 3. Check artifacts
    oof_sha = sha256_file(oof_target) if oof_target.is_file() else None
    sub_file = EXP0_DIR / "submission_exp0.csv"
    sub_sha = sha256_file(sub_file) if sub_file.is_file() else None

    return {
        "exp_no": 0,
        "name": "Exp 0 (Raw LightGBM Baseline with Harness Early-Stopping)",
        "status": exec_res.get("status"),
        "cv_score": exec_res.get("cv_score"),
        "fold_scores": exec_res.get("fold_scores"),
        "wall_time_seconds": round(elapsed, 2),
        "script_sha256": script_sha,
        "oof_sha256": oof_sha,
        "submission_sha256": sub_sha,
        "submission_file": str(sub_file) if sub_file.is_file() else None,
        "exit_code": exec_res.get("exit_code"),
        "stdout_tail": (exec_res.get("stdout") or "")[-800:],
        "stderr_tail": (exec_res.get("stderr") or "")[-800:]
    }


async def run_exp2_repro(runner: LocalRunner) -> dict:
    print("\n" + "=" * 80)
    print("▶ STARTING EXP 2 REPRODUCTION (RUN 050809 EXACT SCRIPT)")
    print("=" * 80)
    EXP2_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Setup files
    scaffold_dst = EXP2_DIR / "run_scaffold.py"
    shutil.copy2(SCAFFOLD_SRC, scaffold_dst)

    folds_dst = EXP2_DIR / "folds.json"
    if not folds_dst.is_file() or sha256_file(folds_dst) != sha256_file(FROZEN_FOLDS_PATH):
        shutil.copy2(FROZEN_FOLDS_PATH, folds_dst)

    model_dst = EXP2_DIR / "model_part_exp2.py"
    shutil.copy2(ORIGINAL_EXP2_SCRIPT, model_dst)
    script_sha = sha256_file(model_dst)
    print(f"Exp 2 script copied from {ORIGINAL_EXP2_SCRIPT} to {model_dst} | SHA-256: {script_sha}")

    # 2. Execute via LocalRunner inside Firejail
    start_time = time.time()
    oof_target = EXP2_DIR / "oof_exp2.parquet"
    cmd_args = [
        "--run-dir", str(EXP2_DIR),
        "--data-dir", str(DATA_DIR),
        "--folds-file", str(folds_dst),
        "--model-module", str(model_dst),
        "--exp-no", "2"
    ]
    print(f"Launching sandboxed execution via Firejail...")
    exec_res = await runner.execute_script(scaffold_dst, args=cmd_args, verify_oof=True, oof_file=oof_target)
    elapsed = time.time() - start_time
    print(f"Exp 2 reproduction finished in {elapsed:.2f}s | Exit code: {exec_res.get('exit_code')}")

    # 3. Check artifacts
    oof_sha = sha256_file(oof_target) if oof_target.is_file() else None
    sub_file = EXP2_DIR / "submission_exp2.csv"
    sub_sha = sha256_file(sub_file) if sub_file.is_file() else None

    return {
        "exp_no": 2,
        "name": "Exp 2 Reproduction (050809 amount_time_interaction)",
        "status": exec_res.get("status"),
        "cv_score": exec_res.get("cv_score"),
        "fold_scores": exec_res.get("fold_scores"),
        "wall_time_seconds": round(elapsed, 2),
        "script_sha256": script_sha,
        "oof_sha256": oof_sha,
        "submission_sha256": sub_sha,
        "exit_code": exec_res.get("exit_code"),
        "stdout_tail": (exec_res.get("stdout") or "")[-800:],
        "stderr_tail": (exec_res.get("stderr") or "")[-800:]
    }


async def main():
    print(f"System checking directories and preconditions...")
    assert DATA_DIR.is_dir(), f"DATA_DIR missing: {DATA_DIR}"
    assert FROZEN_FOLDS_PATH.is_file(), f"FROZEN_FOLDS_PATH missing: {FROZEN_FOLDS_PATH}"
    assert ORIGINAL_EXP2_SCRIPT.is_file(), f"ORIGINAL_EXP2_SCRIPT missing: {ORIGINAL_EXP2_SCRIPT}"

    runner0 = LocalRunner(run_dir=EXP0_DIR, data_dir=DATA_DIR, folds_file=FROZEN_FOLDS_PATH, timeout_seconds=1200)
    runner2 = LocalRunner(run_dir=EXP2_DIR, data_dir=DATA_DIR, folds_file=FROZEN_FOLDS_PATH, timeout_seconds=1200)

    # Run Exp 0
    res0 = await run_exp0(runner0)

    # Run Exp 2 Repro
    res2 = await run_exp2_repro(runner2)

    # Statistical Paired Comparison
    exp0_folds = [res0["fold_scores"][str(f)] for f in range(5)] if res0.get("fold_scores") else []
    exp2_folds = [res2["fold_scores"][str(f)] for f in range(5)] if res2.get("fold_scores") else []

    paired_verdict = compute_paired_verdict(exp2_folds, exp0_folds) if (exp0_folds and exp2_folds) else {}

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "exp0": res0,
        "exp2_repro": res2,
        "paired_comparison": paired_verdict
    }

    summary_file = PROJECT_ROOT / "artifacts" / "kaggle" / "s6e11" / "step3_execution_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print("STEP 3 EXECUTION COMPLETE")
    print(f"Summary written to: {summary_file}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
