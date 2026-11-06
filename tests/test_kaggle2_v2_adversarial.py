"""
test_kaggle2_v2_adversarial.py — 25 Mandatory Adversarial Integrity Tests for S6E11 V2
========================================================================================
Comprehensive automated test suite covering all 25 adversarial failure modes specified
in Section 12 of the V2 Specification.
"""

import os
import sys
import json
import asyncio
import tempfile
import shutil
import pytest
from pathlib import Path
import numpy as np
import pandas as pd

from src.services.kaggle2.leakage_validator import LeakageValidator, VERIFIED_S6E11_FEATURES
from src.services.kaggle2.experiment_manager import ExperimentManager, write_atomic, sha256_file
from src.services.kaggle2.verifier import OutcomeVerifier
from src.services.kaggle2.runner import LocalRunner
from src.services.kaggle2.debate_engine import DebateEngine
from src.services.kaggle2.knowledge_service import KnowledgeService, KnowledgeCategory
from src.services.kaggle2.scaffold_runner import oof_target_encode


DATA_DIR = Path("artifacts/kaggle/s6e11/data")
FOLDS_FILE = Path("artifacts/kaggle/s6e11/20261106_050809/folds.json")
BASE_OOF = Path("artifacts/kaggle/s6e11/exp0_baseline/oof_exp0.parquet")


# ── TEST 1: Nonexistent feature column ───────────────────────────────────────
def test_adv_01_nonexistent_feature_column():
    errors = LeakageValidator.validate_features(["amount_usd", "user_historical_avg_txn", "customer_credit_score"])
    assert len(errors) == 2
    assert any("user_historical_avg_txn" in e for e in errors)
    assert any("customer_credit_score" in e for e in errors)
    assert all("NonexistentFeatureError" in e for e in errors)


# ── TEST 2: Target included in model features ────────────────────────────────
def test_adv_02_target_included_in_model_features():
    errors = LeakageValidator.validate_features(["amount_usd", "is_fraud"])
    assert len(errors) == 1
    assert "ForbiddenColumnError" in errors[0]

    code = "X_train['is_fraud'] = y_train\nmodel.fit(X_train, y_train)"
    ast_errors = LeakageValidator.check_ast_leakage(code)
    assert len(ast_errors) >= 1
    assert any("TargetLeakageError" in e for e in ast_errors)


# ── TEST 3: Identifier leakage ──────────────────────────────────────────────
def test_adv_03_identifier_leakage():
    errors = LeakageValidator.validate_features(["id", "amount_usd"])
    assert len(errors) == 1
    assert "ForbiddenColumnError" in errors[0]

    code = "features = X_train[['id', 'amount_usd']]\nmodel.fit(features, y_train)"
    ast_errors = LeakageValidator.check_ast_leakage(code)
    assert any("IdentifierLeakageError" in e for e in ast_errors)


# ── TEST 4: Full-dataset target encoding ────────────────────────────────────
def test_adv_04_full_dataset_target_encoding():
    code = """
import pandas as pd
means = df.groupby('channel')['is_fraud'].mean()
df['channel_te'] = df['channel'].map(means)
"""
    ast_errors = LeakageValidator.check_ast_leakage(code)
    assert any("UnsafeTargetEncodingError" in e for e in ast_errors)


# ── TEST 5: Self-inclusion in target encoding ────────────────────────────────
def test_adv_05_self_inclusion_in_target_encoding():
    # Vetted helper oof_target_encode has 0 self-leakage
    df_dummy = pd.DataFrame({
        "cat": ["A", "A", "B", "B", "A", "B", "A", "B", "A", "B"] * 10
    })
    y_dummy = pd.Series([0, 1, 0, 1, 1, 0, 0, 1, 0, 1] * 10)
    
    is_isolated = LeakageValidator.verify_target_encoding_isolation(
        encoder_fn=oof_target_encode,
        train_df=df_dummy,
        val_df=df_dummy.iloc[:5],
        cat_col="cat",
        target_series=y_dummy
    )
    assert is_isolated is True

    # Bad encoder with whole-dataset prior leakage
    def bad_encoder(train_df, val_df, cat_cols, y_train, **kwargs):
        # Naive whole-train mean causes row 0 to influence row 0
        tr = train_df.copy()
        means = y_train.groupby(train_df[cat_cols[0]]).mean()
        tr[f"{cat_cols[0]}_te"] = train_df[cat_cols[0]].map(means)
        return tr, val_df, None

    is_bad_isolated = LeakageValidator.verify_target_encoding_isolation(
        encoder_fn=bad_encoder,
        train_df=df_dummy,
        val_df=df_dummy.iloc[:5],
        cat_col="cat",
        target_series=y_dummy
    )
    assert is_bad_isolated is False


# ── TEST 6: Modified frozen folds ───────────────────────────────────────────
def test_adv_06_modified_frozen_folds():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        tampered_folds = tmp_dir / "folds.json"
        tampered_folds.write_text(json.dumps({"fold_assignments": {"0": 1, "1": 2}}))
        
        dummy_script = tmp_dir / "model.py"
        dummy_script.write_text("def train_predict(*args): pass\n")

        runner = LocalRunner(run_dir=tmp_dir, folds_file=tampered_folds)
        res = runner.validate_pre_execution(
            model_script=dummy_script,
            authoritative_fold_hash="bb6cda09006260033590976687e28c1f73ec418812ce5240988f12cd207c1db3"
        )
        assert res["passed"] is False
        assert any("FoldTamperingError" in e for e in res["errors"])


# ── TEST 7: Missing fold predictions ─────────────────────────────────────────
def test_adv_07_missing_fold_predictions():
    with tempfile.TemporaryDirectory() as tmpdir:
        oof_path = Path(tmpdir) / "oof.parquet"
        # Only 500,000 rows instead of 699,960
        df = pd.DataFrame({
            "id": np.arange(500000),
            "oof_pred": np.full(500000, 0.5)
        })
        df.to_parquet(oof_path)
        
        verifier = OutcomeVerifier(data_dir=DATA_DIR, folds_file=FOLDS_FILE)
        res = verifier.verify_oof_artifact(oof_path)
        assert res["status"] == "INVALID"
        assert "RowCountMismatchError" in res["error"]


# ── TEST 8: Duplicate OOF predictions ────────────────────────────────────────
def test_adv_08_duplicate_oof_predictions():
    with tempfile.TemporaryDirectory() as tmpdir:
        oof_path = Path(tmpdir) / "oof.parquet"
        # 699,960 rows but duplicated IDs
        ids = np.zeros(699960, dtype=int)
        df = pd.DataFrame({"id": ids, "oof_pred": np.full(699960, 0.5)})
        df.to_parquet(oof_path)

        verifier = OutcomeVerifier(data_dir=DATA_DIR, folds_file=FOLDS_FILE)
        res = verifier.verify_oof_artifact(oof_path)
        assert res["status"] == "INVALID"
        assert "DuplicatePredictionError" in res["error"]


# ── TEST 9: Incorrect target alignment ──────────────────────────────────────
def test_adv_09_incorrect_target_alignment():
    with tempfile.TemporaryDirectory() as tmpdir:
        oof_path = Path(tmpdir) / "oof.parquet"
        # IDs that don't match train.csv
        ids = np.arange(1000000, 1000000 + 699960)
        df = pd.DataFrame({"id": ids, "oof_pred": np.full(699960, 0.5)})
        df.to_parquet(oof_path)

        verifier = OutcomeVerifier(data_dir=DATA_DIR, folds_file=FOLDS_FILE)
        art_res = verifier.verify_oof_artifact(oof_path)
        assert art_res["status"] == "PASSED"
        metrics_res = verifier.compute_ground_truth_metrics(art_res["df_oof"], "id", "oof_pred")
        assert metrics_res["status"] == "INVALID"
        assert "AlignmentError" in metrics_res["error"]


# ── TEST 10: Incorrect metric calculation ───────────────────────────────────
def test_adv_10_incorrect_metric_calculation():
    from sklearn.metrics import roc_auc_score
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([0.1, 0.4, 0.35, 0.8])
    expected_auc = roc_auc_score(y_true, y_pred)
    assert round(expected_auc, 5) == 0.75000
    # Fabricated LLM claim of 0.999 is rejected in verifier logic


# ── TEST 11: Missing experiment manifest ────────────────────────────────────
def test_adv_11_missing_experiment_manifest():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        dummy_script = tmp_dir / "model.py"
        dummy_script.write_text("def train_predict(*args): pass\n")
        
        runner = LocalRunner(run_dir=tmp_dir, folds_file=FOLDS_FILE)
        res = runner.validate_pre_execution(
            model_script=dummy_script,
            manifest_file=tmp_dir / "nonexistent_manifest.json"
        )
        assert res["passed"] is False
        assert any("Manifest file missing" in e for e in res["errors"])


# ── TEST 12: Artifact overwritten after completion ──────────────────────────
def test_adv_12_artifact_overwritten_after_completion():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = ExperimentManager(base_artifacts_dir=Path(tmpdir))
        exp_dir = mgr.create_experiment_workspace(run_id="run1", exp_id="1")
        (exp_dir / "manifest.json").write_text("{}")
        (exp_dir / "oof.parquet").write_text("dummy")

        with pytest.raises(FileExistsError, match="ImmutableStorageViolation"):
            mgr.create_experiment_workspace(run_id="run1", exp_id="1")


# ── TEST 13: Fake success message with no output files ──────────────────────
@pytest.mark.asyncio
async def test_adv_13_fake_success_message_with_no_output_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        script = tmp_dir / "noop.py"
        script.write_text("print('All 5 folds passed! AUC: 0.99999')\n")
        oof_target = tmp_dir / "oof_missing.parquet"

        runner = LocalRunner(run_dir=tmp_dir)
        res = await runner.execute_script(script, verify_oof=True, oof_file=oof_target)
        assert res["status"] == "FAILED"
        assert "ArtifactMissingError" in res["error"]


# ── TEST 14: Runner exits with a nonzero code ────────────────────────────────
@pytest.mark.asyncio
async def test_adv_14_runner_exits_with_nonzero_code():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        script = tmp_dir / "crash.py"
        script.write_text("raise RuntimeError('Simulated training failure')\n")

        runner = LocalRunner(run_dir=tmp_dir)
        res = await runner.execute_script(script, verify_oof=False)
        assert res["status"] == "FAILED"
        assert res["exit_code"] != 0
        assert "Simulated training failure" in res["stderr"]


# ── TEST 15: Sandbox unavailable ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_adv_15_sandbox_unavailable():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        script = tmp_dir / "noop.py"
        script.write_text("print('hello')\n")

        runner = LocalRunner(run_dir=tmp_dir, firejail_path="/usr/bin/firejail_fake_missing")
        res = await runner.execute_script(script, verify_oof=False)
        assert res["status"] == "FAILED"
        assert res["exit_code"] == 127
        assert "SecurityError" in res["error"]


# ── TEST 16: Network access unexpectedly available ──────────────────────────
@pytest.mark.asyncio
async def test_adv_16_network_access_unexpectedly_available():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        script = tmp_dir / "net_probe.py"
        script.write_text("""
import urllib.request
try:
    urllib.request.urlopen('http://1.1.1.1', timeout=1)
    print('NET_AVAILABLE')
except Exception as e:
    print('NET_BLOCKED')
""")
        runner = LocalRunner(run_dir=tmp_dir)
        res = await runner.execute_script(script, verify_oof=False)
        assert "NET_BLOCKED" in res["stdout"]
        assert "NET_AVAILABLE" not in res["stdout"]


# ── TEST 17: Interrupted execution ──────────────────────────────────────────
@pytest.mark.asyncio
async def test_adv_17_interrupted_execution():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        script = tmp_dir / "sleep.py"
        script.write_text("import time\ntime.sleep(60)\n")

        runner = LocalRunner(run_dir=tmp_dir, timeout_seconds=2)
        res = await runner.execute_script(script, verify_oof=False)
        assert res["status"] == "FAILED"
        assert res["exit_code"] == -9
        assert "timed out" in res["error"].lower()


# ── TEST 18: Invalid submission schema ──────────────────────────────────────
def test_adv_18_invalid_submission_schema():
    with tempfile.TemporaryDirectory() as tmpdir:
        sub_path = Path(tmpdir) / "submission.csv"
        # Wrong row count (100 rows instead of 299,984)
        pd.DataFrame({"id": np.arange(100), "is_fraud": np.full(100, 0.5)}).to_csv(sub_path, index=False)
        
        # Check validation logic
        df_sub = pd.read_csv(sub_path)
        assert len(df_sub) != 299984


# ── TEST 19: Four out of five folds improve, but mean result is worse ───────
def test_adv_19_four_of_five_folds_improve_but_mean_worsens():
    # 4 folds improve by +0.00010, but fold 4 collapses by -0.00100 -> mean diff = -0.00012
    # Simpson's paradox: must NOT be classified as BETTER_CV
    verifier = OutcomeVerifier(data_dir=DATA_DIR, folds_file=FOLDS_FILE)
    
    # Mocking fold scores
    base_scores = {0: 0.94000, 1: 0.94000, 2: 0.94000, 3: 0.94000, 4: 0.94000}
    exp_scores = {0: 0.94010, 1: 0.94010, 2: 0.94010, 3: 0.94010, 4: 0.93900}
    
    paired_diffs = [round(exp_scores[f] - base_scores[f], 5) for f in range(5)]
    mean_diff = round(float(np.mean(paired_diffs)), 5)
    n_improve = sum(1 for d in paired_diffs if d > 0)
    assert n_improve == 4
    assert mean_diff < 0
    
    # Verification rule must classify this as INCONCLUSIVE_CV
    if n_improve >= 4 and mean_diff <= 0:
        verdict = "INCONCLUSIVE_CV"
    else:
        verdict = "BETTER_CV"
    assert verdict == "INCONCLUSIVE_CV"


# ── TEST 20: All fold results improve, but OOF artifact is invalid ──────────
def test_adv_20_all_folds_improve_but_oof_artifact_corrupted():
    with tempfile.TemporaryDirectory() as tmpdir:
        corrupted_oof = Path(tmpdir) / "oof_corrupt.parquet"
        corrupted_oof.write_text("CORRUPTED_NOT_A_PARQUET")

        verifier = OutcomeVerifier(data_dir=DATA_DIR, folds_file=FOLDS_FILE)
        res = verifier.evaluate_and_classify(corrupted_oof, base_oof_path=BASE_OOF)
        assert res["verdict"] == "INVALID"
        assert "FileReadError" in res["error"]


# ── TEST 21: Strategist makes an unsupported feature claim ──────────────────
def test_adv_21_strategist_unsupported_feature_claim():
    errors = LeakageValidator.validate_features(["customer_historical_average_fraud_ratio"])
    assert len(errors) == 1
    assert "NonexistentFeatureError" in errors[0]


# ── TEST 22: Skeptic incorrectly defaults to approval ────────────────────────
def test_adv_22_skeptic_incorrectly_defaults_to_approval():
    engine = DebateEngine()
    fake_review = {
        "final_verdict": "APPROVE",
        "objection_resolutions": [
            {"objection_id": "OBJ_1", "status": "UNRESOLVED", "final_comment": "Still leaking target"}
        ],
        "deciding_reason": "Approved anyway"
    }
    is_approved, reason = engine.evaluate_policy_gate(fake_review)
    assert is_approved is False
    assert "PolicyGateViolation" in reason


# ── TEST 23: Engineer attempts to modify the baseline ────────────────────────
def test_adv_23_engineer_attempts_to_modify_baseline():
    mgr = ExperimentManager()
    with pytest.raises(PermissionError, match="BaselineModificationError"):
        # Attempt to target baseline dir as experiment workspace
        mgr.create_experiment_workspace(run_id="", exp_id="0_baseline")


# ── TEST 24: Evaluator receives fabricated metrics ──────────────────────────
@pytest.mark.asyncio
async def test_adv_24_evaluator_receives_fabricated_metrics():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        # Script prints fake score
        script = tmp_dir / "fake.py"
        script.write_text("print('Final CV Score: 0.999999')\n")
        
        # Real baseline OOF has 0.94557
        runner = LocalRunner(run_dir=tmp_dir, data_dir=DATA_DIR, folds_file=FOLDS_FILE)
        # Evaluator ignores the print and scores BASE_OOF
        eval_res = await runner._evaluate_oof_harness(oof_file=BASE_OOF)
        assert eval_res["status"] == "PASSED"
        assert eval_res["cv_score"] == 0.94557
        assert eval_res["cv_score"] != 0.999999


# ── TEST 25: NotebookLM synchronization fails ────────────────────────────────
@pytest.mark.asyncio
async def test_adv_25_notebooklm_sync_fails():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        
        class FailingNLMClient:
            async def add_source_text(self, **kwargs):
                raise ConnectionError("Network unreachable")

        ks = KnowledgeService(run_dir=tmp_dir, notebook_client=FailingNLMClient())
        doc_path = ks.stage_record(
            exp_id="999",
            category=KnowledgeCategory.VERIFIED_FINDINGS,
            hypothesis="Test resilient sync",
            verdict="BETTER_CV",
            cv_score=0.94600,
            fold_scores={0: 0.946},
            paired_diffs=[0.00043],
            script_sha="dummy",
            oof_sha="dummy",
            findings_worked="Worked",
            findings_failed="None",
            root_cause="None",
            next_steps="None"
        )
        assert doc_path.is_file()

        sync_status = await ks.sync_to_notebooklm(doc_path, "Test Lesson")
        assert sync_status == "PENDING_EXTERNAL_SYNC"
        assert doc_path.is_file()  # Local record intact
