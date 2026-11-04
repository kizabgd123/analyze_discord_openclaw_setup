"""
test_layered_services.py — Integration & Unit Tests for Services and Repositories.
==================================================================================
Verifies layer isolation, data access, and JudgeGuard safety boundaries.
"""

import unittest
import tempfile
from pathlib import Path
from src.repositories.rag_repository import RAGRepository
from src.repositories.state_repository import StateRepository
from src.services.judge_guard_service import JudgeGuardService


class TestLayeredServices(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.rag_db = self.temp_path / "test_rag.db"
        self.rag_repo = RAGRepository(db_path=self.rag_db)

        self.work_log = self.temp_path / "WORK_LOG.md"
        self.work_log.write_text("🟡 Starting test\n")
        self.state_repo = StateRepository(
            openclaw_path=self.temp_path / "openclaw.json",
            debate_state_path=self.temp_path / "debate_state.json",
            memory_path=self.temp_path / "MEMORY.md",
            work_log_path=self.work_log
        )
        self.judge_service = JudgeGuardService(state_repo=self.state_repo)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_rag_repository_insert_and_search(self):
        # Insert
        ok = self.rag_repo.insert_document(
            doc_id="doc-1",
            source="manual",
            title="Arhitektura",
            body="OpenClaw koristi slojevitu arhitekturu sa servisima i kontrolerima."
        )
        self.assertTrue(ok)
        self.assertEqual(self.rag_repo.count_documents(), 1)

        # FTS Search
        results = self.rag_repo.search_fts("arhitekturu")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "doc-1")
        self.assertEqual(results[0]["title"], "Arhitektura")

    def test_judge_guard_verify_action_safe(self):
        passed, msg = self.judge_service.verify_action("uptime")
        self.assertTrue(passed)
        self.assertIn("PASSED", msg)

    def test_judge_guard_verify_action_blocked(self):
        passed, msg = self.judge_service.verify_action("rm -rf /")
        self.assertFalse(passed)
        self.assertIn("Dangerous operation rejected", msg)

    def test_state_repository_debate_state(self):
        test_state = {"status": "in_progress", "round": 2}
        saved = self.state_repo.save_debate_state(test_state)
        self.assertTrue(saved)

        loaded = self.state_repo.load_debate_state()
        self.assertEqual(loaded.get("status"), "in_progress")
        self.assertEqual(loaded.get("round"), 2)


if __name__ == "__main__":
    unittest.main()
