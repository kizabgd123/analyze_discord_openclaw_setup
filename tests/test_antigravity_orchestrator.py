"""
test_antigravity_orchestrator.py — Tests for Layer A Agent Manager & Baseline Invariance
========================================================================================
Validates requirements 11-18:
  11. Antigravity Agent Manager role isolation (5 distinct Layer A roles).
  12. Single-writer path collision detection.
  13. Stale file-lock recovery.
  14. Scope enforcement for all 5 roles.
  15. Verification hooks triggering properly.
  16. Unchanged baseline hash (Exp 0 baseline invariance).
  17. Unchanged frozen folds hash.
  18. Absence of Kaggle submission triggers.
"""

import os
import time
import hashlib
from pathlib import Path
import pytest

from scripts.antigravity_orchestrator import AgentPoolManager


@pytest.fixture
def agent_manager():
    return AgentPoolManager()


# ── Test 11: Antigravity Agent Manager role isolation ──
def test_11_antigravity_agent_manager_role_isolation(agent_manager):
    agents = agent_manager.get_agent_names()
    expected_roles = {
        "frontend-agent",
        "backend-agent",
        "intercom-agent",
        "memory-agent",
        "quality-guard"
    }
    assert set(agents) == expected_roles, f"Expected exactly {expected_roles}, got {set(agents)}"

    # Verify that Kaggle experiment roles (Strategist, Skeptic, Engineer, Runner, Evaluator)
    # are NOT in the Layer A software development pool
    kaggle_layer_b_roles = {"strategist", "skeptic", "engineer", "runner", "evaluator"}
    assert kaggle_layer_b_roles.isdisjoint(set(agents))


# ── Test 12: Single-writer path collision detection ──
def test_12_single_writer_path_collision_detection(agent_manager):
    # Overlapping path
    paths_frontend = ["src/services/kaggle2/html_generator.py", "src/dashboard/shared.py"]
    paths_backend = ["src/services/kaggle2/agent_team.py", "src/dashboard/shared.py"]

    collisions = agent_manager.detect_path_collisions("frontend-agent", paths_frontend, "backend-agent", paths_backend)
    assert len(collisions) == 1
    assert "src/dashboard/shared.py" in collisions[0]

    # Non-overlapping paths
    paths_disjoint_a = ["src/services/kaggle2/html_generator.py"]
    paths_disjoint_b = ["src/services/kaggle2/agent_team.py"]
    no_collisions = agent_manager.detect_path_collisions("frontend-agent", paths_disjoint_a, "backend-agent", paths_disjoint_b)
    assert len(no_collisions) == 0


# ── Test 13: Stale file-lock recovery ──
def test_13_stale_file_lock_recovery(agent_manager, tmp_path):
    manager = AgentPoolManager(stale_lock_seconds=1)
    res_name = "test_shared_module.py"

    # Agent A acquires lock
    ok_a = manager.acquire_lock("agent-a", res_name)
    assert ok_a is True

    # Immediate second acquire by Agent B must fail
    ok_b = manager.acquire_lock("agent-b", res_name)
    assert ok_b is False

    # Simulate stale lock by backdating mtime by 5 seconds
    lock_file = manager.lock_dir / f"{res_name}.lock"
    old_time = time.time() - 10
    os.utime(lock_file, (old_time, old_time))

    # Now Agent B should succeed due to automatic stale lock recovery
    ok_b_recovered = manager.acquire_lock("agent-b", res_name)
    assert ok_b_recovered is True
    assert lock_file.read_text(encoding="utf-8").strip() == "agent-b"

    # Cleanup
    manager.release_lock("agent-b", res_name)


# ── Test 14: Scope enforcement for all 5 roles ──
def test_14_scope_enforcement_for_all_5_roles(agent_manager):
    # 1. frontend-agent: can edit html_generator, cannot edit test suites or baseline
    ok_fe, _ = agent_manager.validate_file_access("frontend-agent", ["src/services/kaggle2/html_generator.py"])
    assert ok_fe is True
    ok_fe_bad, _ = agent_manager.validate_file_access("frontend-agent", ["tests/test_infra.py"])
    assert ok_fe_bad is False

    # 2. backend-agent: can edit runner and agent_team, cannot touch baseline
    ok_be, _ = agent_manager.validate_file_access("backend-agent", ["src/services/kaggle2/runner.py"])
    assert ok_be is True
    ok_be_bad, _ = agent_manager.validate_file_access("backend-agent", ["artifacts/kaggle/s6e11/exp0_baseline/oof_exp0.parquet"])
    assert ok_be_bad is False

    # 3. intercom-agent: can edit discord, cannot touch model runner
    ok_ic, _ = agent_manager.validate_file_access("intercom-agent", ["src/discord/bot.py"])
    assert ok_ic is True
    ok_ic_bad, _ = agent_manager.validate_file_access("intercom-agent", ["src/services/kaggle2/runner.py"])
    assert ok_ic_bad is False

    # 4. memory-agent: can edit notebook client & lessons, cannot touch baseline
    ok_mem, _ = agent_manager.validate_file_access("memory-agent", ["src/services/kaggle2/notebook_client.py"])
    assert ok_mem is True
    ok_mem_bad, _ = agent_manager.validate_file_access("memory-agent", ["artifacts/kaggle/s6e11/exp0_baseline/oof_exp0.parquet"])
    assert ok_mem_bad is False

    # 5. quality-guard: can edit tests, cannot tamper with baseline
    ok_qg, _ = agent_manager.validate_file_access("quality-guard", ["tests/test_new_suite.py"])
    assert ok_qg is True
    ok_qg_bad, _ = agent_manager.validate_file_access("quality-guard", ["artifacts/kaggle/s6e11/exp0_baseline/oof_exp0.parquet"])
    assert ok_qg_bad is False


# ── Test 15: Verification hooks triggering properly ──
def test_15_verification_hooks_triggering_properly(agent_manager):
    for role in agent_manager.get_agent_names():
        hook_info = agent_manager.verify_hooks(role)
        assert hook_info["agent"] == role
        assert hook_info["ready"] is True
        assert len(hook_info["hooks"]) > 0


# ── Test 16: Unchanged baseline hash ──
def test_16_unchanged_baseline_hash():
    baseline_oof = Path("artifacts/kaggle/s6e11/exp0_baseline/oof_exp0.parquet")
    assert baseline_oof.is_file(), f"Exp 0 baseline file missing at {baseline_oof}"

    h = hashlib.sha256(baseline_oof.read_bytes()).hexdigest()
    expected_prefix = "b630ff38999088"
    assert h.startswith(expected_prefix), f"Exp 0 OOF hash changed! Expected prefix {expected_prefix}, got {h}"


# ── Test 17: Unchanged frozen folds hash ──
def test_17_unchanged_frozen_folds_hash():
    folds_file = Path("artifacts/kaggle/s6e11/exp0_baseline/folds.json")
    assert folds_file.is_file(), f"Frozen folds file missing at {folds_file}"

    h = hashlib.sha256(folds_file.read_bytes()).hexdigest()
    expected_prefix = "bb6cda090062"
    assert h.startswith(expected_prefix), f"Frozen folds hash changed! Expected prefix {expected_prefix}, got {h}"


# ── Test 18: Absence of Kaggle submission triggers ──
def test_18_absence_of_kaggle_submission_triggers():
    # Scan source tree to ensure automated loops do not automatically call 'kaggle competitions submit'
    repo_root = Path(__file__).resolve().parent.parent
    agent_team_py = (repo_root / "src" / "services" / "kaggle2" / "agent_team.py").read_text(encoding="utf-8")
    orchestrator_py = (repo_root / "scripts" / "antigravity_orchestrator.py").read_text(encoding="utf-8")

    # In Layer A orchestrator, kaggle commands must not exist
    assert "kaggle competitions submit" not in orchestrator_py

    # In AgentTeam autonomous loop, submissions must strictly require explicit user triggers
    # Verify that run_single_experiment does not auto-submit
    assert "submission_service.submit_to_kaggle" not in agent_team_py
