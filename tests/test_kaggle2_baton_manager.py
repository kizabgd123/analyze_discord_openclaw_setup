"""
test_kaggle2_baton_manager.py — Verification of KGMON Baton Manager
====================================================================
Tests:
  1. Initialization of synthetic features cookbook.
  2. Generation of 4 authoritative markdown files:
     - plan.md
     - progress.md
     - discoveries.md
     - closed_ideas.md
  3. Content inspection for required tables and frozen fold hashes.
"""

import tempfile
from pathlib import Path
import pytest

from src.services.kaggle2.baton_manager import BatonManager, COOKBOOKS_DIR, SYNTHETIC_COOKBOOK_PATH


def test_baton_manager_initialize_cookbooks():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = BatonManager(run_dir=Path(tmpdir))
        cb_path = manager.initialize_cookbooks()
        assert cb_path.exists()
        content = cb_path.read_text(encoding="utf-8")
        assert "extract_digit_trie_features" in content
        assert "oof_target_encode_smooth" in content


def test_baton_manager_update_baton_creates_all_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        manager = BatonManager(run_dir=run_dir, competition="playground-series-s6e11")

        state = {
            "run_id": "test_run_baton_01",
            "folds_info": "StratifiedKFold (n_splits=5) — FROZEN",
            "authoritative_fold_hash": "bb6cda09006260033590976687e28c1f73ec418812ce5240988f12cd207c1db3",
            "experiments": [
                {
                    "exp_no": 0,
                    "hypothesis": "Baseline LightGBM 24 features",
                    "skeptic_verdict": "BASELINE",
                    "cv_score": 0.94557,
                    "verdict_vs_base": "BASELINE",
                    "status": "PASSED",
                    "phase_timings": {"runner_seconds": 15.2},
                    "deciding_reason": "Audited reference baseline",
                    "oof_sha256": "abcdef123456",
                    "script_sha256": "fedcba654321"
                },
                {
                    "exp_no": 1,
                    "hypothesis": "Digit trie components on amount_usd",
                    "skeptic_verdict": "APPROVE",
                    "cv_score": 0.94612,
                    "verdict_vs_base": "+0.00055",
                    "status": "PASSED",
                    "phase_timings": {"runner_seconds": 22.1},
                    "deciding_reason": "CV ROC-AUC improved beyond threshold",
                    "oof_sha256": "112233445566",
                    "script_sha256": "665544332211"
                }
            ],
            "failures": [
                {
                    "type": "SCRIPT_CRASH",
                    "title": "Broken model part",
                    "raw_error": "SyntaxError: invalid syntax",
                    "timestamp": "2026-11-07 10:00:00"
                }
            ],
            "blocked_hypotheses": [
                "Direct target encoding without inner fold splitting"
            ]
        }

        res = manager.update_baton(state)

        for key in ("plan", "progress", "discoveries", "closed_ideas", "cookbooks"):
            assert key in res
            f_path = Path(res[key])
            assert f_path.exists(), f"File {f_path} does not exist"

        # Check plan.md
        plan_content = Path(res["plan"]).read_text(encoding="utf-8")
        assert "Plan Istraživanja" in plan_content
        assert "test_run_baton_01" in plan_content
        assert "01_EDA" in plan_content

        # Check progress.md
        prog_content = Path(res["progress"]).read_text(encoding="utf-8")
        assert "KGMON Progress Report" in prog_content
        assert "bb6cda09006260033590976687e28c1f73ec418812ce5240988f12cd207c1db3" in prog_content
        assert "0.94557" in prog_content
        assert "0.94612" in prog_content

        # Check discoveries.md
        disc_content = Path(res["discoveries"]).read_text(encoding="utf-8")
        assert "Verifikovana Otkrića" in disc_content
        assert "Exp #1" in disc_content
        assert "0.94612" in disc_content

        # Check closed_ideas.md
        closed_content = Path(res["closed_ideas"]).read_text(encoding="utf-8")
        assert "Lista Zatvorenih Ideja" in closed_content
        assert "SyntaxError: invalid syntax" in closed_content
        assert "Direct target encoding without inner fold splitting" in closed_content
