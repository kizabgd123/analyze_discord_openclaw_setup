"""
test_base_controller.py — Unit Tests for BaseController Standard.
=================================================================
Verifies input validation, error handling, and response encapsulation.
"""

import unittest
from unittest.mock import AsyncMock, MagicMock
from pydantic import ValidationError
from src.controllers.base_controller import BaseController
from src.validators.nlm_schemas import AskQuerySchema


class TestBaseController(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.controller = BaseController(name="TestController")

    def test_validate_payload_success(self):
        result = self.controller.validate_payload(
            AskQuerySchema,
            {"query": "Test pitanje"}
        )
        self.assertIsInstance(result, AskQuerySchema)
        self.assertEqual(result.query, "Test pitanje")

    def test_validate_payload_failure(self):
        with self.assertRaises(ValidationError):
            self.controller.validate_payload(
                AskQuerySchema,
                {"query": ""}
            )

    async def test_handle_success_interaction(self):
        mock_interaction = MagicMock()
        mock_interaction.response.is_done.return_value = True
        mock_interaction.followup.send = AsyncMock()

        await self.controller.handle_success(
            mock_interaction,
            data="Odgovor",
            title="Naslov"
        )
        mock_interaction.followup.send.assert_awaited_once()

    async def test_handle_error_interaction(self):
        mock_interaction = MagicMock()
        mock_interaction.response.is_done.return_value = True
        mock_interaction.followup.send = AsyncMock()

        dummy_error = ValueError("Kritična greška")
        await self.controller.handle_error(
            dummy_error,
            mock_interaction,
            action_name="test_action"
        )
        mock_interaction.followup.send.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
