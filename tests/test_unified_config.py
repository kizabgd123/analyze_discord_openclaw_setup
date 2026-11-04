"""
test_unified_config.py — Unit Tests for Centralized Unified Configuration.
==========================================================================
Verifies single source of truth and type compliance.
"""

import unittest
from pathlib import Path
from src.config.unified_config import config, UnifiedConfig


class TestUnifiedConfig(unittest.TestCase):

    def test_config_instance(self):
        self.assertIsInstance(config, UnifiedConfig)
        self.assertEqual(config.project_name, "discord-openclaw")
        self.assertEqual(config.version, "2.0.0")

    def test_discord_config(self):
        self.assertIsNotNone(config.discord.command_prefix)
        self.assertIsInstance(config.discord.auto_sync_tree, bool)

    def test_nlm_config(self):
        self.assertTrue(config.nlm.binary_path.endswith("nlm"))
        self.assertIn("3bd81caf", config.nlm.orchestration_notebook_id)
        self.assertGreater(config.nlm.timeout_seconds, 0)

    def test_agy_config(self):
        self.assertEqual(len(config.agy.accounts), 4)
        self.assertIn("promo@mrcleanervracar.com", config.agy.accounts)
        self.assertEqual(config.agy.default_model, "gemini-3.8-flash-high")

    def test_database_paths(self):
        self.assertTrue(str(config.db.rag_db_path).endswith("antigravity_rag.db"))
        self.assertTrue(str(config.db.openclaw_json_path).endswith("openclaw.json"))
        self.assertTrue(str(config.db.work_log_path).endswith("WORK_LOG.md"))

    def test_judge_guard_config(self):
        self.assertEqual(config.judge_guard.freshness_window_seconds, 300)
        self.assertIsNotNone(config.judge_guard.secret)

    def test_litert_config(self):
        self.assertIn(".litertlm", config.litert.model_path)
        self.assertIn(config.litert.backend, ["auto", "gpu", "cpu", "npu"])
        self.assertIsInstance(config.litert.enable_speculative_decoding, bool)
        self.assertIsInstance(config.litert.enabled, bool)
        self.assertIsInstance(config.litert.allow_all_tools, bool)

    def test_local_openai_config(self):
        self.assertEqual(config.local_openai.model, "gemma2:2b")
        self.assertIn("11434", config.local_openai.base_url)
        self.assertIsInstance(config.local_openai.enabled, bool)
        self.assertIsInstance(config.local_openai.apply_lightweight, bool)


if __name__ == "__main__":
    unittest.main()
