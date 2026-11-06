"""
test_kaggle2_debate_and_scaffold.py — Verification Suite for Scaffold, Debate with Teeth, and NLM Logging.
========================================================================================================
Covers requirements F(1), F(2), and F(3):
  1. Folds parsing safely extracts fold assignments, ignores metadata keys (e.g. 'scheme', 'n_splits'),
     and verifies every train.csv row has exactly one fold id.
  2. Forced BLOCK verdict halts execution: Engineer is NEVER called, model_part.py is NOT generated,
     and HTML dashboard renders a BLOCKED row with the deciding reason.
  3. Agent-written questions appear verbatim in state log and HTML dashboard along with their author.
"""

import os
import sys
import json
import asyncio
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.services.kaggle2.agent_team import AgentTeamOrchestrator
from src.services.kaggle2.html_generator import render_html_dashboard


def test_f1_folds_safe_parsing_and_scheme_rejection():
    """
    F(1): Loads folds.json and verifies every train.csv row has exactly one fold id
    and rejects/ignores metadata keys such as 'scheme', 'n_splits', 'created_at'.
    Runs inside runner_venv where pandas and numpy are installed.
    """
    runner_python = Path("runner_venv/bin/python3").resolve()
    assert runner_python.is_file(), f"runner_venv python must exist at {runner_python}"

    test_code = """
import os
import sys
import json
import tempfile
from pathlib import Path
import pandas as pd
import numpy as np

from src.services.kaggle2.scaffold_runner import run_experiment_scaffold

with tempfile.TemporaryDirectory() as tmpdir:
    tmp_path = Path(tmpdir)
    train_path = tmp_path / "train.csv"
    folds_path = tmp_path / "folds.json"
    run_dir = tmp_path / "run_01"
    run_dir.mkdir(parents=True, exist_ok=True)

    n_samples = 30
    df = pd.DataFrame({
        "id": np.arange(n_samples),
        "amount_usd": np.random.uniform(5, 500, n_samples),
        "feature1": np.random.randn(n_samples),
        "is_fraud": np.random.choice([0.0, 1.0], n_samples, p=[0.9, 0.1])
    })
    df.to_csv(train_path, index=False)

    # Build folds.json containing metadata keys like 'scheme', 'n_splits'
    assignments = {str(i): int(i % 5) for i in range(n_samples)}
    raw_folds = {
        "scheme": "StratifiedKFold",
        "n_splits": 5,
        "random_state": 42,
        "created_at": "2026-11-06T00:00:00Z",
        "fold_assignments": assignments
    }
    with open(folds_path, "w", encoding="utf-8") as f:
        json.dump(raw_folds, f)

    # Minimal model module
    model_module_path = run_dir / "model_part.py"
    model_module_path.write_text(
        "import numpy as np\\n"
        "def train_predict(X_tr, y_tr, X_val, y_val):\\n"
        "    return np.full(len(X_val), 0.15)\\n"
    )

    # Run scaffold
    run_experiment_scaffold(
        run_dir=run_dir,
        data_dir=tmp_path,
        folds_file=folds_path,
        model_module_path=model_module_path
    )

    oof_file = run_dir / "oof_predictions.parquet"
    assert oof_file.is_file(), "oof_predictions.parquet must be generated"
    oof_df = pd.read_parquet(oof_file)
    assert len(oof_df) == n_samples
    assert set(oof_df["fold"].unique()) == {0, 1, 2, 3, 4}
    assert "scheme" not in oof_df.columns

    # Verify missing fold assignment raises FoldAlignmentError / ValueError
    bad_assignments = {str(i): int(i % 5) for i in range(n_samples - 2)} # 2 missing
    bad_folds = {"scheme": "StratifiedKFold", "fold_assignments": bad_assignments}
    bad_folds_path = tmp_path / "bad_folds.json"
    with open(bad_folds_path, "w", encoding="utf-8") as f:
        json.dump(bad_folds, f)

    try:
        run_experiment_scaffold(
            run_dir=run_dir,
            data_dir=tmp_path,
            folds_file=bad_folds_path,
            model_module_path=model_module_path
        )
        sys.exit(1) # Should not reach here
    except ValueError as e:
        assert "FoldAlignmentError: 2 samples" in str(e)
        print("OK: Missing folds correctly rejected")

print("SUCCESS: Folds parsing and metadata rejection verified.")
"""

    res = subprocess.run(
        [str(runner_python), "-c", test_code],
        env={"PYTHONPATH": os.getcwd(), "PATH": os.environ["PATH"]},
        capture_output=True,
        text=True
    )
    assert res.returncode == 0, f"Subprocess failed with stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    assert "SUCCESS: Folds parsing and metadata rejection verified." in res.stdout


@pytest.mark.asyncio
async def test_f2_forced_block_skips_engineer_and_logs_blocked_in_html():
    """
    F(2): A forced BLOCK verdict leads to no Engineer call and a BLOCKED row in the HTML.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test_block_run"
        tmp_path = Path(tmpdir)
        orch = AgentTeamOrchestrator(run_id=run_id, data_dir=tmp_path)
        orch.run_dir = tmp_path
        orch.state_file = tmp_path / "state.json"
        orch.html_file = tmp_path / "view.html"
        orch.folds_file = tmp_path / "folds.json"
        orch.is_running = True

        engineer_called = False

        def mock_query_llm(prompt, system=None, **kwargs):
            nonlocal engineer_called
            p_upper = prompt.upper()
            s_upper = (system or "").upper()

            if "YOU ARE THE ML ENGINEER" in p_upper or "YOU ARE THE ML ENGINEER" in s_upper:
                engineer_called = True
                return "```python\ndef train_predict(): pass\n```"

            if "FORMULATE ONE SPECIFIC RESEARCH QUESTION" in p_upper:
                return "BRIEF: What are the strongest baseline models for fraud detection?"

            if "YOU ARE THE STRATEGIST. BASED ON RESEARCH" in p_upper:
                return (
                    "HYPOTHESIS: Train an external ResNet-50 pre-trained on ImageNet using external data.\n"
                    "FEATURE_ENGINEERING: Convert transactions to images.\n"
                    "MODEL_FAMILY: External Pre-trained CNN.\n"
                    "EXPECTED_IMPACT: Massive boost."
                )

            if "YOU ARE THE SKEPTIC. REVIEW THE STRATEGIST'S PROPOSAL" in p_upper:
                return (
                    "VERDICT: BLOCK\n"
                    "REASON: rule violation: Competition strictly prohibits external pre-trained foundation models."
                )

            if "THE SKEPTIC BLOCKED YOUR PROPOSAL" in p_upper:
                return "I insist on using external pre-trained weights because they learn faster."

            if "RENDER YOUR FINAL VERDICT" in p_upper:
                return (
                    "FINAL_VERDICT: BLOCK\n"
                    "FINAL_REASON: rule violation: external pre-trained weights remain banned."
                )

            if "STATE YOUR FORMAL DECISION" in p_upper:
                return (
                    "DECISION: BLOCKED\n"
                    "DECIDING_REASON: Prohibited external pre-trained weights."
                )

            return "OK"

        # Mock query_notebook
        async def mock_query_notebook(question):
            return {"status": "PASSED", "answer": "External models and data are prohibited by rules.", "citations": {}}

        with patch("gemini_client.query_llm", side_effect=mock_query_llm), \
             patch.object(orch.notebook_client, "query_notebook", side_effect=mock_query_notebook):

            res = await orch.run_single_experiment(exp_no=1)

            assert res["status"] == "BLOCKED"
            assert res["cv_score"] is None
            assert engineer_called is False, "Engineer MUST NOT be invoked when proposal is BLOCKED!"
            assert not (orch.run_dir / "model_part.py").exists(), "model_part.py must NOT be created!"

            # Verify HTML dashboard contains BLOCKED badge and reason
            assert orch.html_file.is_file()
            html_content = orch.html_file.read_text(encoding="utf-8")
            assert "badge-blocked" in html_content
            assert "BLOCKED" in html_content
            assert "Prohibited external pre-trained weights" in html_content


@pytest.mark.asyncio
async def test_f3_agent_written_question_logged_with_author():
    """
    F(3): An agent-written question appears in the log with its author.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test_nlm_author_run"
        tmp_path = Path(tmpdir)
        orch = AgentTeamOrchestrator(run_id=run_id, data_dir=tmp_path)
        orch.run_dir = tmp_path
        orch.state_file = tmp_path / "state.json"
        orch.html_file = tmp_path / "view.html"
        orch.folds_file = tmp_path / "folds.json"

        async def mock_query_notebook(question):
            return {"status": "PASSED", "answer": "Target encoding without cross-validation causes leakage.", "citations": {}}

        with patch.object(orch.notebook_client, "query_notebook", side_effect=mock_query_notebook):
            # Strategist asks
            await orch.ask_notebook(
                agent_name="Strategist",
                question="BRIEF: Which categorical encodings are recommended for tree models?",
                reason="strategist_technique_search"
            )

            # Skeptic asks
            await orch.ask_notebook(
                agent_name="Skeptic",
                question="CHECK: Does target encoding cause severe target leakage without out-of-fold calculation?",
                reason="skeptic_fact_check"
            )

        # Check state.json logs
        queries = orch.state["nlm_queries"]
        assert len(queries) == 2
        assert queries[0]["agent"] == "Strategist"
        assert queries[0]["reason"] == "strategist_technique_search"
        assert "Which categorical encodings" in queries[0]["question"]

        assert queries[1]["agent"] == "Skeptic"
        assert queries[1]["reason"] == "skeptic_fact_check"
        assert "target leakage" in queries[1]["question"]

        # Check HTML dashboard rendering
        html_content = orch.html_file.read_text(encoding="utf-8")
        assert "[Strategist | strategist_technique_search]" in html_content
        assert "[Skeptic | skeptic_fact_check]" in html_content
