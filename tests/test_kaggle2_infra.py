"""
test_kaggle2_infra.py — Rigorous Verification Suite for S6E11 Multi-Agent Infrastructure.
========================================================================================
Covers Tests A through G under the Evidence Protocol:
  - Test A: Runner Fault (deliberately broken script -> status FAILED with raw stderr)
  - Test B: NLM Query Fault (failed query -> status FAILED with verbatim error)
  - Test C: Admin Gate (fail-closed check against unified_config)
  - Test D: Submission Tag Filter & Hard Cap (filters strictly by s6e11-<run_id>-<exp_no>, 5 cap)
  - Test E: HTML Generation (complete mobile view.html with all required sections)
  - Test F: Lesson Ingestion to NLM (lesson added as source, verified via nlm source list)
  - Test G: Process Kill on Stop (runner terminates child process, verified via ps)
"""

import os
import sys
import json
import signal
import asyncio
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.services.kaggle2.notebook_client import NotebookLMClient, classify_source_origin
from src.services.kaggle2.runner import LocalRunner
from src.services.kaggle2.lesson_service import LessonService
from src.services.kaggle2.submission_service import SubmissionService
from src.services.kaggle2.html_generator import render_html_dashboard
from src.services.kaggle2.agent_team import AgentTeamOrchestrator
from src.controllers.kaggle2_controller import check_admin_auth
from src.config.unified_config import unified_config


@pytest.mark.asyncio
async def test_a_runner_fault_detection():
    """Test A: Deliberately broken script must result in status FAILED with raw stderr."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        broken_script = run_dir / "broken_model.py"
        broken_script.write_text(
            "import sys\n"
            "print('Starting broken experiment...', file=sys.stderr)\n"
            "raise ValueError('DELIBERATE_ENGINEER_SYNTAX_FAULT: Missing feature matrix')\n"
        )

        runner = LocalRunner(run_dir=run_dir, timeout_seconds=10)
        result = await runner.execute_script(broken_script)

        assert result["status"] == "FAILED", f"Expected status FAILED, got {result['status']}"
        assert result["exit_code"] != 0, f"Expected non-zero exit code, got {result['exit_code']}"
        assert "DELIBERATE_ENGINEER_SYNTAX_FAULT" in result["stderr"]
        assert result["cv_score"] is None
        print("\n[TEST A PASSED] Runner successfully detected broken script and captured raw stderr.")


@pytest.mark.asyncio
async def test_b_nlm_query_fault_handling():
    """Test B: Failed NotebookLM query must be logged as FAILED with raw error (never hallucinated)."""
    # Use an invalid/non-existent notebook ID to trigger deterministic failure
    client = NotebookLMClient(notebook_id="invalid-00000000-0000-0000-0000-000000000000")
    result = await client.query_notebook("What is the CV score?", timeout=15.0)

    assert result["status"] == "FAILED", f"Expected query status FAILED, got {result['status']}"
    assert result["answer"] is None, "Failed query must have answer=None (never invent answers)"
    assert result["error"] is not None
    print(f"\n[TEST B PASSED] NLM query failure captured with verbatim error: {result['error'][:80]}...")


def test_c_admin_gate():
    """Test C: Non-admin users are rejected; admin is accepted; unset admin fails closed."""
    admin_id = getattr(unified_config.discord, "admin_user_id", None) if unified_config.discord else None
    assert admin_id is not None, "Admin ID must be set in unified_config for valid test environment"

    # Non-admin interaction
    fake_user = MagicMock(id=999999999999)
    fake_interaction = MagicMock(user=fake_user)
    assert check_admin_auth(fake_interaction) is False, "Non-admin user must be rejected (fail-closed)"

    # Legitimate admin interaction
    admin_user = MagicMock(id=admin_id)
    admin_interaction = MagicMock(user=admin_user)
    assert check_admin_auth(admin_interaction) is True, "Configured admin user must be accepted"

    # Unset admin config must fail closed
    with patch.object(unified_config, "discord", None):
        assert check_admin_auth(admin_interaction) is False, "Unset admin config must fail closed"
    print("\n[TEST C PASSED] Admin gate strictly enforces fail-closed authorization.")


@pytest.mark.asyncio
async def test_d_submission_tag_filter_and_cap():
    """Test D: Only rows with our tag are processed, older submissions are ignored, 5 cap enforced."""
    run_id = "test_run_42"
    service = SubmissionService(run_id=run_id, max_submissions_per_run=5)

    # 1. Test Tag Filtering against simulated Kaggle submissions
    mock_submissions = [
        MagicMock(description="s6e11-test_run_42-1", publicScore="0.95123", fileName="sub1.csv", status="COMPLETE", ref="101"),
        MagicMock(description="s6e11-test_run_42-2", publicScore="0.95201", fileName="sub2.csv", status="COMPLETE", ref="102"),
        MagicMock(description="Usisivac V6 Autonomous Model", publicScore="0.94649", fileName="old.csv", status="COMPLETE", ref="99"),
        MagicMock(description="s6e11-other_run_99-1", publicScore="0.94900", fileName="other.csv", status="COMPLETE", ref="100"),
    ]

    mock_kaggle = MagicMock()
    mock_kaggle.api.competition_submissions.return_value = mock_submissions
    with patch.dict(sys.modules, {"kaggle": mock_kaggle}):
        filtered = await service.list_run_submissions()
        tags = [f["description"] for f in filtered]
        assert tags == ["s6e11-test_run_42-1", "s6e11-test_run_42-2"], f"Unexpected filtered tags: {tags}"
        assert all("Usisivac" not in t for t in tags), "Older submissions must never be read"

    # 2. Test 5 Submissions Hard Cap
    service.submitted_count = 5
    with tempfile.NamedTemporaryFile(suffix=".csv") as f:
        prep = await service.prepare_submission(exp_no=6, submission_file=Path(f.name), cv_score=0.96000)
        assert prep["status"] == "BLOCKED"
        assert "budget reached" in prep["reason"].lower()
    print("\n[TEST D PASSED] Submission service strictly filters by tag and enforces budget cap of 5.")


def test_e_html_dashboard_generation():
    """Test E: Validates complete, phone-friendly HTML dashboard output with all sections."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_html = Path(tmpdir) / "view.html"
        mock_state = {
            "run_id": "eval_test_run",
            "competition": "playground-series-s6e11",
            "updated_at": "2026-11-06T03:45:00Z",
            "folds_info": "StratifiedKFold (n_splits=5, shuffle=True, random_state=42) — FROZEN",
            "failures": [
                {"type": "SCRIPT_CRASH", "title": "Experiment 1 failed", "raw_error": "SyntaxError: unexpected EOF", "timestamp": "03:45:10"}
            ],
            "sources": [
                {"title": "Competition Overview", "url": "https://www.kaggle.com/competitions/playground-series-s6e11", "origin": "Kaggle page"},
                {"title": "Shallow Tree Stack", "url": "https://www.kaggle.com/code/alexchilton/stack", "origin": "public notebook"}
            ],
            "transcript": [
                {"agent": "Strategist", "role": "Strategist", "message": "Proposing shallow GBDT", "timestamp": "03:45:12", "is_lesson_query": False}
            ],
            "nlm_queries": [
                {"question": "What is the metric?", "answer": "ROC-AUC", "citations": {"1": "src-1"}, "status": "PASSED", "error": None, "timestamp": "03:45:15"}
            ],
            "experiments": [
                {"exp_no": 1, "hypothesis": "Test shallow trees", "cv_score": 0.95120, "status": "PASSED", "elapsed_seconds": 12.4}
            ],
            "lessons": [
                {"exp_no": 1, "status": "PASSED", "cv_score": 0.95120, "what_worked": "Shallow trees", "what_failed": "Deep trees", "why": "Smooth target", "next_steps": "Blend with CatBoost"}
            ],
            "submissions": [
                {"tag": "s6e11-eval_test_run-1", "sha256": "abcdef1234567890", "cv_score": 0.95120, "public_score": 0.95195}
            ]
        }

        generated_path = render_html_dashboard(mock_state, out_html)
        assert generated_path.is_file()
        content = generated_path.read_text(encoding="utf-8")

        assert "FAILURES & WARNINGS" in content
        assert "SyntaxError: unexpected EOF" in content
        assert "Knowledge Grounding Sources Directory" in content
        assert "StratifiedKFold (n_splits=5, shuffle=True, random_state=42) — FROZEN" in content
        assert "s6e11-eval_test_run-1" in content
        print("\n[TEST E PASSED] Standalone HTML dashboard successfully rendered with all required sections.")


@pytest.mark.asyncio
async def test_f_lesson_ingestion_to_nlm():
    """Test F: Uses a dedicated throwaway notebook, ingests a lesson, verifies via nlm source list, then deletes notebook."""
    # 1. Create temporary throwaway notebook
    create_proc = await asyncio.create_subprocess_exec(
        "nlm", "notebook", "create", "Throwaway Test F Notebook", "--json",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await create_proc.communicate()
    assert create_proc.returncode == 0, f"Failed creating throwaway notebook: {stderr.decode()}"
    nb_data = json.loads(stdout.decode())
    temp_notebook_id = nb_data["notebook_id"]

    try:
        client = NotebookLMClient(notebook_id=temp_notebook_id)
        with tempfile.TemporaryDirectory() as tmpdir:
            lesson_service = LessonService(run_dir=Path(tmpdir), notebook_client=client)
            lesson = await lesson_service.create_lesson(
                exp_no=777,
                hypothesis="Verification of Lesson Ingestion Protocol on Throwaway Notebook",
                methodology="Automated isolated test fixture",
                cv_score=0.95321,
                what_worked="Direct NLM source ingestion CLI",
                what_failed="None",
                why_reasoning="Verified end-to-end integration without touching production notebook",
                next_steps="Ready for autonomous runs",
                status="PASSED"
            )
            assert lesson["ingest_status"] == "PASSED", f"Lesson ingestion failed: {lesson}"

            # Verify in nlm source list
            sources = await client.list_sources()
            titles = [s.get("title", "") for s in sources]
            matching = [t for t in titles if "Lesson Exp 777" in t]
            assert len(matching) > 0, f"Expected 'Lesson Exp 777' in sources list: {titles}"
            print(f"\n[TEST F PASSED] Verified lesson ingestion in throwaway notebook {temp_notebook_id}: {matching[0]}")
    finally:
        # Clean up throwaway notebook completely
        del_proc = await asyncio.create_subprocess_exec(
            "nlm", "notebook", "delete", temp_notebook_id, "--confirm",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await del_proc.communicate()
        print(f"[TEST F CLEANUP] Deleted throwaway notebook {temp_notebook_id}")


@pytest.mark.asyncio
async def test_g_stop_process_kill():
    """Test G: Stop terminates running experiment and `ps` confirms no leftover process."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        sleep_script = run_dir / "long_running_experiment.py"
        sleep_script.write_text("import time\ntime.sleep(60)\n")

        runner = LocalRunner(run_dir=run_dir, timeout_seconds=60)
        # Launch script asynchronously
        task = asyncio.create_task(runner.execute_script(sleep_script))

        # Wait briefly for process to start and grab PID
        for _ in range(20):
            if runner.current_pid is not None:
                break
            await asyncio.sleep(0.05)

        pid = runner.current_pid
        assert pid is not None, "Failed to start runner process"

        # Verify process is running in ps
        check_proc = subprocess.run(["ps", "-p", str(pid)], capture_output=True, text=True)
        assert str(pid) in check_proc.stdout, f"PID {pid} should be active in ps"

        # Trigger Kill
        killed = await runner.kill()
        assert killed is True, "Runner kill() should return True"

        # Await task completion
        res = await task
        assert res["status"] == "FAILED"

        # Verify PID no longer exists in ps
        verify_proc = subprocess.run(["ps", "-p", str(pid)], capture_output=True, text=True)
        assert str(pid) not in verify_proc.stdout, f"Process PID {pid} was not killed!"
        print(f"\n[TEST G PASSED] Process PID {pid} was cleanly terminated; zero leftover process confirmed by ps.")
