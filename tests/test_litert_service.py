"""
test_litert_service.py — Unit Tests for LiteRTAgentService.
=============================================================
Tests hardware backend auto-detection, config generation,
status verification, and local execution pipeline.
"""

import os
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

from google.antigravity import LiteRTAgentConfig, LocalOpenAIAgentConfig, LiteRTBackend
from src.services.litert_agent_service import LiteRTAgentService, LiteRTModelNotFoundError
from src.config.unified_config import UnifiedConfig, LiteRTConfig, LocalOpenAIConfig


class TestLiteRTAgentService(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.custom_cfg = UnifiedConfig()
        self.service = LiteRTAgentService(cfg=self.custom_cfg)

    def test_resolve_model_path_expands_user(self):
        resolved = self.service.resolve_model_path("~/.litert-lm/test.litertlm")
        self.assertNotIn("~", str(resolved))
        self.assertTrue(str(resolved).endswith("test.litertlm"))

    def test_detect_best_backend_configured_cpu(self):
        self.custom_cfg.litert.backend = "cpu"
        backend = self.service.detect_best_backend()
        self.assertEqual(backend, LiteRTBackend.CPU)

    def test_detect_best_backend_configured_gpu(self):
        self.custom_cfg.litert.backend = "gpu"
        backend = self.service.detect_best_backend()
        self.assertEqual(backend, LiteRTBackend.GPU)

    def test_detect_best_backend_auto_fallback_to_cpu_when_no_nvidia(self):
        self.custom_cfg.litert.backend = "auto"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            backend = self.service.detect_best_backend()
            self.assertEqual(backend, LiteRTBackend.CPU)

    def test_check_status_returns_required_keys(self):
        status = self.service.check_status()
        self.assertIn("model_path", status)
        self.assertIn("model_exists", status)
        self.assertIn("model_size_mb", status)
        self.assertIn("litert_cli_available", status)
        self.assertIn("imported_models", status)
        self.assertIn("detected_backend", status)
        self.assertIn("workspace_dir", status)

    def test_build_litert_config(self):
        test_path = "/tmp/test_model.litertlm"
        agent_cfg = self.service.build_litert_config(
            model_path=test_path,
            backend=LiteRTBackend.CPU,
            workspace_dir="/tmp/test_workspace",
            enable_speculative_decoding=True,
            system_instructions="Test instruction",
            allow_all_tools=True
        )
        self.assertIsInstance(agent_cfg, LiteRTAgentConfig)
        self.assertEqual(agent_cfg.model_path, test_path)
        self.assertEqual(agent_cfg.backend, LiteRTBackend.CPU)
        self.assertTrue(agent_cfg.enable_speculative_decoding)
        self.assertEqual(agent_cfg.workspaces, ["/tmp/test_workspace"])
        self.assertIsNotNone(agent_cfg.policies)

    def test_build_local_openai_config(self):
        agent_cfg = self.service.build_local_openai_config(
            model="gemma4:26b",
            base_url="http://localhost:11434/v1",
            workspace_dir="/tmp/test_workspace",
            system_instructions="Test instructions",
            allow_all_tools=True
        )
        self.assertIsInstance(agent_cfg, LocalOpenAIAgentConfig)
        self.assertEqual(agent_cfg.model, "gemma4:26b")
        self.assertEqual(agent_cfg.base_url, "http://localhost:11434/v1")
        self.assertEqual(agent_cfg.workspaces, ["/tmp/test_workspace"])

    async def test_chat_raises_when_model_missing_and_no_external_server(self):
        self.custom_cfg.litert.model_path = "/nonexistent/path/model.litertlm"
        self.custom_cfg.local_openai.enabled = False

        with self.assertRaises(LiteRTModelNotFoundError) as ctx:
            await self.service.chat("Hello local model")

        self.assertIn("LiteRT model fajl nije pronađen", str(ctx.exception))
        self.assertIn("litert-lm import", str(ctx.exception))

    async def test_chat_stream_mock_agent(self):
        # Mock Agent and response generator
        mock_tokens = ["Hello", " from", " local", " LiteRT!"]

        async def token_generator():
            for t in mock_tokens:
                yield t

        mock_agent_instance = AsyncMock()
        mock_agent_instance.chat = AsyncMock(return_value=token_generator())

        mock_agent_cm = AsyncMock()
        mock_agent_cm.__aenter__.return_value = mock_agent_instance
        mock_agent_cm.__aexit__.return_value = None

        with patch("src.services.litert_agent_service.Agent", return_value=mock_agent_cm):
            with patch.object(self.service, "check_status") as mock_status:
                mock_status.return_value = {
                    "model_path": "/tmp/dummy.litertlm",
                    "model_exists": True,
                    "model_size_mb": 100.0,
                    "litert_cli_available": True,
                    "imported_models": ["gemma4-26b"],
                    "detected_backend": "cpu",
                    "workspace_dir": "/tmp/test",
                }
                result = await self.service.chat("Hello")
                self.assertEqual(result, "Hello from local LiteRT!")


if __name__ == "__main__":
    unittest.main()
