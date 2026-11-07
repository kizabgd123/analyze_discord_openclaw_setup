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


@pytest.mark.asyncio
async def test_h_pre_execution_leakage_and_fold_hash_blocking():
    """
    Test H (Slice 1 — Real E2E): Instantiates a real AgentTeamOrchestrator and calls
    run_single_experiment(). A model script with AST leakage (target encoding without
    inner folds) MUST be blocked by validate_pre_execution() BEFORE the runner starts.

    Verifies:
      1. runner.execute_script is NEVER called.
      2. state["experiments"] receives a record with status="BLOCKED_PRE_EXECUTION".
      3. state["failures"] receives a record with type="PRE_EXECUTION_INTEGRITY_VIOLATION".
      4. BatonManager writes the failure to closed_ideas.md on disk.
    """
    import hashlib
    import asyncio
    from unittest.mock import patch, AsyncMock, MagicMock
    from gemini_client import LLMResponse
    from src.services.kaggle2.agent_team import AgentTeamOrchestrator

    # --- Deterministic LLM stub ---
    # Returns a valid proposal JSON on first call, then bland text for all subsequent calls.
    _call_count = {"n": 0}
    VALID_PROPOSAL_JSON = json.dumps({
        "hypothesis": "Use LightGBM with frequency encoding on merchant_category",
        "hypothesis_id": "EXP1_LGBM_FREQ_ENC",
        "feature_engineering": ["frequency encoding on merchant_category"],
        "model_family": "LightGBM",
        "expected_delta_cv": 0.001,
        "leakage_risk": "none — no target statistics used",
        "literature_reference": "Prokhorenkova et al. 2018, CatBoost paper",
        "implementation_complexity": "low",
        "compute_budget_hours": 0.5
    })

    def mock_llm_call(prompt, system=None, **kwargs):
        _call_count["n"] += 1
        n = _call_count["n"]
        # Turn 1 → valid proposal; all others → harmless text that parses as BLOCK
        text = VALID_PROPOSAL_JSON if n == 1 else "VERDICT: PROCEED\nDECIDING_REASON: OK"
        return LLMResponse(
            text=text,
            provider="mock",
            model="mock-model",
            account=None,
            latency_seconds=0.001,
            fallback_chain=[],
            exit_code=0,
        )

    def mock_query_llm(prompt, system=None, **kwargs):
        return mock_llm_call(prompt, system=system, **kwargs).text

    with tempfile.TemporaryDirectory() as tmpdir:
        run_id = "test_run_slice1_e2e"
        run_dir = Path(tmpdir) / "artifacts" / "kaggle" / "s6e11" / run_id

        # Patch NotebookLMClient to avoid real network calls
        with patch("src.services.kaggle2.agent_team.NotebookLMClient") as MockNLM, \
             patch("src.services.kaggle2.agent_team.LessonService") as MockLS, \
             patch("src.services.kaggle2.agent_team.SubmissionService"), \
             patch("src.services.kaggle2.agent_team.query_llm_with_lineage", side_effect=mock_llm_call), \
             patch("src.services.kaggle2.agent_team.query_llm", side_effect=mock_query_llm):

            # Configure NLM mock
            mock_nlm_inst = MockNLM.return_value
            mock_nlm_inst.query_notebook = AsyncMock(return_value={"answer": "No context found", "sources": []})
            mock_nlm_inst.add_source = AsyncMock(return_value={"status": "ok"})

            # Configure LessonService mock
            mock_ls_inst = MockLS.return_value
            mock_ls_inst.create_lesson = AsyncMock(return_value={"file_path": str(run_dir / "lesson.md"), "status": "ok"})

            # Instantiate with a tmp-aware run_dir via monkeypatch of Path base
            with patch("src.services.kaggle2.agent_team.Path") as MockPath:
                # Use real Path everywhere except we redirect the run_dir construction
                MockPath.side_effect = lambda *args, **kw: Path(*args, **kw)

                orchestrator = AgentTeamOrchestrator(run_id=run_id)

            # Redirect to our tempdir AFTER construction
            orchestrator.run_dir = run_dir
            run_dir.mkdir(parents=True, exist_ok=True)
            orchestrator.state_file = run_dir / "state.json"
            orchestrator.state = orchestrator._load_or_create_state()
            orchestrator.baton_manager.run_dir = run_dir  # redirect MD output

            # Create a leaky model_part.py BEFORE run_single_experiment
            # so that the engineer turn picks it up (we patch the engineer LLM too)
            leaky_code = (
                "import pandas as pd\n"
                "def train_predict(X_train, y_train, X_val, y_val):\n"
                "    target_means = y_train.groupby(X_train['cat']).mean()\n"
                "    X_train['cat_te'] = X_train['cat'].map(target_means)\n"
                "    return [0.5]\n"
            )

            # Patch engineer code generation to inject our leaky script
            original_open = open
            write_calls = []

            def patched_open(path, mode="r", **kw):
                p = Path(path)
                if "model_part" in p.name and "w" in mode:
                    write_calls.append(str(p))
                    # Write leaky code instead of whatever LLM generated
                    import builtins
                    fh = builtins.open(path, mode, **kw)
                    return fh
                return original_open(path, mode, **kw)

            # Simpler approach: just set the engineer LLM to produce leaky code
            leaky_llm_calls = {"n": 0}

            def mock_llm_with_leaky_engineer(prompt, system=None, **kwargs):
                leaky_llm_calls["n"] += 1
                n = leaky_llm_calls["n"]
                # Turn 1 (proposal) → valid proposal JSON
                # Turn 2+ (all LLM calls incl. engineer) → leaky code for engineer, PROCEED for others
                if n == 1:
                    text = VALID_PROPOSAL_JSON
                elif "ML Engineer" in (system or ""):
                    text = f"```python\n{leaky_code}\n```"
                else:
                    text = "VERDICT: PROCEED\nDECIDING_REASON: OK"
                return LLMResponse(
                    text=text,
                    provider="mock",
                    model="mock-model",
                    account=None,
                    latency_seconds=0.001,
                    fallback_chain=[],
                    exit_code=0,
                )

            def mock_llm_plain(prompt, system=None, **kwargs):
                return mock_llm_with_leaky_engineer(prompt, system=system, **kwargs).text

            with patch("src.services.kaggle2.agent_team.query_llm_with_lineage", side_effect=mock_llm_with_leaky_engineer), \
                 patch("src.services.kaggle2.agent_team.query_llm", side_effect=mock_llm_plain), \
                 patch.object(orchestrator.runner, "execute_script") as mock_exec:

                # Set a known folds file + authoritative hash to allow fold check to pass
                # (we want the AST leakage check to be the trigger, not fold hash mismatch)
                import hashlib as _hl
                folds_data = b'{"0": [0, 1], "1": [2, 3], "2": [4, 5], "3": [6, 7], "4": [8, 9]}'
                orchestrator.folds_file = run_dir / "folds.json"
                orchestrator.folds_file.write_bytes(folds_data)
                orchestrator.authoritative_fold_hash = _hl.sha256(folds_data).hexdigest()

                orchestrator.is_running = True
                result = await orchestrator.run_single_experiment(exp_no=1)

        # ── Assertions ──
        # 1. Status must be BLOCKED_PRE_EXECUTION
        assert result["status"] == "BLOCKED_PRE_EXECUTION", (
            f"Expected BLOCKED_PRE_EXECUTION, got {result['status']}"
        )

        # 2. runner.execute_script must NEVER have been called
        mock_exec.assert_not_called()

        # 3. experiments list must have a BLOCKED_PRE_EXECUTION record
        blocked_exps = [e for e in orchestrator.state.get("experiments", [])
                        if e.get("status") == "BLOCKED_PRE_EXECUTION"]
        assert len(blocked_exps) >= 1, (
            f"Expected at least 1 BLOCKED_PRE_EXECUTION experiment, found: {orchestrator.state.get('experiments')}"
        )

        # 4. failures list must have a PRE_EXECUTION_INTEGRITY_VIOLATION record
        pei_failures = [f for f in orchestrator.state.get("failures", [])
                        if f.get("type") == "PRE_EXECUTION_INTEGRITY_VIOLATION"]
        assert len(pei_failures) >= 1, (
            f"Expected PRE_EXECUTION_INTEGRITY_VIOLATION failure, found: {orchestrator.state.get('failures')}"
        )

        # 5. BatonManager must have written closed_ideas.md
        orchestrator.baton_manager.update_progress(orchestrator.state)
        closed_path = run_dir / "closed_ideas.md"
        assert closed_path.exists(), "BatonManager must write closed_ideas.md"
        closed_content = closed_path.read_text(encoding="utf-8")
        assert "PRE_EXECUTION_INTEGRITY_VIOLATION" in closed_content, (
            f"Expected PRE_EXECUTION_INTEGRITY_VIOLATION in closed_ideas.md:\n{closed_content}"
        )

    print("\n[TEST H PASSED] Real E2E: AST leakage blocked pre-execution; runner never called; state updated; BatonManager wrote closed_ideas.md.")


def test_i_controller_judgeguard_mtime_and_finally():
    """
    Test I (Slice 3): Zero-mock test using tempfile and os.utime to verify JudgeGuard:
      - Stale log (360s old) -> BLOCKED
      - log_start() updates mtime to t=0 -> PASSED
      - try/finally guarantees log_complete() in WORK_LOG.md
    """
    import time
    from judge_guard import JudgeGuard

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_log = Path(tmpdir) / "WORK_LOG.md"
        temp_log.write_text("2026-11-07T12:00:00Z | 🟡 Starting Previous Task\n", encoding="utf-8")

        # 1. Stale WORK_LOG.md (360 seconds in the past)
        stale_time = time.time() - 360
        os.utime(temp_log, (stale_time, stale_time))

        judge = JudgeGuard(work_log_path=temp_log, freshness_seconds=300)
        action_label = "Kaggle2 Autonomous Cycle Run test_run_infra"

        # Stale log must fail closed to BLOCKED
        verdict = judge.verify(action_label)
        assert verdict == "BLOCKED"

        # 2. log_start() appends start marker and refreshes file mtime
        judge.log_start(action_label)
        verdict_after_start = judge.verify(action_label)
        assert verdict_after_start == "PASSED"

        # 3. Simulate controller execution with try/finally
        try:
            executed = True
        finally:
            judge.log_complete(action_label)

        log_content = temp_log.read_text(encoding="utf-8")
        assert f"🟡 Starting {action_label}" in log_content
        assert f"✅ Completed {action_label}" in log_content


