"""
test_litert_controller.py — Unit Tests for LiteRTController.
=============================================================
Tests input validation, controller responses, error boundaries,
and status generation.
"""

import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from pydantic import ValidationError

from src.controllers.litert_controller import LiteRTController
from src.services.litert_agent_service import LiteRTModelNotFoundError


class TestLiteRTController(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_service = MagicMock()
        self.controller = LiteRTController(service=self.mock_service)
        self.mock_interaction = MagicMock()
        self.mock_interaction.response = MagicMock()
        self.mock_interaction.response.is_done.return_value = True
        self.mock_interaction.followup = AsyncMock()

    async def test_handle_status_success(self):
        self.mock_service.check_status.return_value = {
            "model_path": "/home/user/.litert-lm/models/gemma4-26b/model.litertlm",
            "model_exists": True,
            "model_size_mb": 16800.0,
            "litert_cli_available": True,
            "imported_models": ["gemma4-26b"],
            "detected_backend": "cpu",
            "speculative_decoding": False,
            "workspace_dir": "/tmp/workspace",
            "local_openai_enabled": False,
            "local_openai_base_url": "http://localhost:11434/v1",
            "local_openai_model": "gemma4:26b",
        }

        res = await self.controller.handle_status(self.mock_interaction)
        self.assertTrue(res["ok"])
        self.assertEqual(res["status"]["detected_backend"], "cpu")
        self.mock_interaction.followup.send.assert_called_once()

    async def test_handle_chat_success(self):
        self.mock_service.check_status.return_value = {"detected_backend": "cpu"}
        self.mock_service.chat = AsyncMock(return_value="Local response token stream done.")

        res = await self.controller.handle_chat(
            interaction=self.mock_interaction,
            prompt="Test prompt for LiteRT"
        )
        self.assertTrue(res["ok"])
        self.assertEqual(res["response"], "Local response token stream done.")
        self.mock_interaction.followup.send.assert_called_once()

    async def test_handle_chat_empty_prompt_validation_error(self):
        res = await self.controller.handle_chat(
            interaction=self.mock_interaction,
            prompt="   "
        )
        self.assertFalse(res["ok"])
        self.assertIn("Upit ne može biti prazan", res["error"])

    async def test_handle_chat_model_not_found(self):
        self.mock_service.check_status.return_value = {"detected_backend": "cpu"}
        self.mock_service.get_import_instructions.return_value = "litert-lm import command"
        self.mock_service.chat = AsyncMock(
            side_effect=LiteRTModelNotFoundError("Model not found on path")
        )

        res = await self.controller.handle_chat(
            interaction=self.mock_interaction,
            prompt="Explain quantum computing"
        )
        self.assertFalse(res["ok"])
        self.assertIn("Model not found", res["error"])

    async def test_handle_import_instructions(self):
        self.mock_service.get_import_instructions.return_value = "litert-lm import test"
        res = await self.controller.handle_import_instructions(
            interaction=self.mock_interaction,
            model_name="gemma4-26b"
        )
        self.assertTrue(res["ok"])
        self.assertIn("litert-lm import test", res["instructions"])


if __name__ == "__main__":
    unittest.main()
