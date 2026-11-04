"""
system_controller.py — Controller for System Health, Safety, and Shell Gates.
=============================================================================
Inherits from BaseController. Validates shell commands and enforces JudgeGuard.
"""

from typing import Any, Optional
try:
    import discord
except ImportError:
    discord = None
from src.controllers.base_controller import BaseController
from src.services.judge_guard_service import JudgeGuardService
from src.services.nlm_service import NotebookLMService
from src.validators.system_schemas import ShellCommandSchema
from src.config.unified_config import config


class SystemController(BaseController):
    """Coordinates system diagnostics, status reporting, and safe command execution."""

    def __init__(
        self,
        judge_service: Optional[JudgeGuardService] = None,
        nlm_service: Optional[NotebookLMService] = None
    ):
        super().__init__(name="SystemController")
        self.judge_service = judge_service or JudgeGuardService()
        self.nlm_service = nlm_service or NotebookLMService()

    async def get_status(self, target: Any) -> None:
        """Audits connection health and returns system telemetry."""
        try:
            nlm_health = await self.nlm_service.check_health()
            freshness_ok, freshness_msg = self.judge_service._check_work_log_freshness()

            status_report = (
                f"**Verzija:** `{config.version}`\n"
                f"**Okruženje:** `{config.observability.environment}`\n"
                f"**Google NotebookLM CLI:** `{'ONLINE' if nlm_health.get('ok') else 'OFFLINE'}` ({nlm_health.get('version')})\n"
                f"**JudgeGuard Stanje:** `{'AKTIVNO' if freshness_ok else 'UPOZORENJE'}` ({freshness_msg})\n"
                f"**RAG Baza:** `{config.db.rag_db_path.name}` (`{'PRONAĐENA' if config.db.rag_db_path.exists() else 'NEDOSTAJE'}`)"
            )
            await self.handle_success(
                target,
                status_report,
                title="🩺 OpenClaw Sistem Telemetrija & Zdravlje",
                color=0x34A853 if (nlm_health.get("ok") and freshness_ok) else 0xFBBC05
            )
        except Exception as exc:
            await self.handle_error(exc, target, action_name="get_status")

    async def execute_command(self, target: Any, command: str) -> None:
        """Evaluates shell command through JudgeGuard safety gate."""
        try:
            validated = self.validate_payload(ShellCommandSchema, {"command": command})
            passed, reason = self.judge_service.verify_action(validated.command)

            if not passed:
                raise PermissionError(f"JudgeGuard je blokirao akciju: {reason}")

            # Safe acknowledgement
            await self.handle_success(
                target,
                f"Komanda `{validated.command}` je uspešno autorizovana i potpisana kroz JudgeGuard HMAC.",
                title="🛡️ Sigurnosna Verifikacija Prošla"
            )
        except Exception as exc:
            await self.handle_error(exc, target, action_name="execute_command")
