"""
litert_controller.py — Controller for LiteRT & Local Model Agent Interactions.
=============================================================================
Follows backend-dev-guidelines:
- Inherits from BaseController.
- Strict input validation via LiteRTChatSchema.
- Sentry observability and error boundary handling.
"""

import logging
from typing import Optional, Any, Dict
from src.controllers.base_controller import BaseController
from src.services.litert_agent_service import LiteRTAgentService, LiteRTModelNotFoundError
from src.validators.litert_schemas import LiteRTChatSchema
from src.instrument import capture_exception, capture_message

try:
    import discord
except ImportError:
    discord = None

logger = logging.getLogger("LiteRTController")


class LiteRTController(BaseController):
    """Handles LiteRT and Local Agent Discord commands and requests."""

    def __init__(self, service: Optional[LiteRTAgentService] = None):
        super().__init__(name="LiteRTController")
        self.service = service or LiteRTAgentService()

    async def handle_status(self, interaction: Any) -> Dict[str, Any]:
        """Provides diagnostic information about local LiteRT models and backend."""
        try:
            status = self.service.check_status()
            exists_emoji = "✅ Prisutan" if status["model_exists"] else "❌ Nije pronađen"
            models_str = ", ".join(status["imported_models"]) if status["imported_models"] else "(Nema uvezenih modela)"

            desc = (
                f"**Lokalni model:** `{status['model_path']}`\n"
                f"• Status datoteke: **{exists_emoji}**\n"
                f"• Veličina: `{status['model_size_mb']} MB`\n"
                f"• Detektovani hardver backend: **`{status['detected_backend'].upper()}`**\n"
                f"• CLI alat `litert-lm`: {'✅ Dostupan' if status['litert_cli_available'] else '❌ Nedostupan'}\n"
                f"• Registrovani modeli u `~/.litert-lm/models`: `{models_str}`\n"
                f"• Radni direktorijum: `{status['workspace_dir']}`\n"
                f"• Spekulativno dekodovanje: `{'Uključeno' if status['speculative_decoding'] else 'Isključeno'}`\n\n"
                f"**Eksterni OpenAI server:**\n"
                f"• Status: `{'Omogućen' if status['local_openai_enabled'] else 'Onemogućen'}`\n"
                f"• URL: `{status['local_openai_base_url']}` | Model: `{status['local_openai_model']}`"
            )

            await self.handle_success(
                interaction,
                data=desc,
                title="⚡ Google AI Edge LiteRT — Status Lokalne Izvršne Jedinice",
                color=0x4285F4
            )
            return {"ok": True, "status": status}
        except Exception as exc:
            await self.handle_error(exc, interaction, "litert_status")
            return {"ok": False, "error": str(exc)}

    async def handle_chat(
        self,
        interaction: Any,
        prompt: str,
        workspace_dir: Optional[str] = None,
        system_instructions: Optional[str] = None,
        use_external_server: bool = False,
    ) -> Dict[str, Any]:
        """Executes a prompt against local LiteRTAgent with input validation."""
        try:
            payload = {
                "prompt": prompt,
                "workspace_dir": workspace_dir,
                "system_instructions": system_instructions,
                "use_external_server": use_external_server,
            }
            validated = self.validate_payload(LiteRTChatSchema, payload)

            status = self.service.check_status()
            logger.info(f"[LiteRTController] Running chat on backend={status['detected_backend']}...")

            response_text = await self.service.chat(
                prompt=validated.prompt,
                system_instructions=validated.system_instructions,
                workspace_dir=validated.workspace_dir,
                use_external_server=validated.use_external_server,
            )

            title = "🤖 LiteRT Agent Odgovor (Lokalni Model)"
            if validated.use_external_server:
                title = "🤖 Local OpenAI Agent Odgovor"

            await self.handle_success(
                interaction,
                data=response_text,
                title=title,
                color=0x34A853
            )
            return {"ok": True, "response": response_text}

        except LiteRTModelNotFoundError as mnf_err:
            instructions = self.service.get_import_instructions()
            user_msg = (
                f"⚠️ Lokalni `.litertlm` checkpoint nije pronađen.\n\n"
                f"{str(mnf_err)}\n\n"
                f"Pokrenite sledeću komandu za preuzimanje:\n{instructions}"
            )
            await self.handle_error(mnf_err, interaction, "litert_chat", user_friendly_msg=user_msg)
            return {"ok": False, "error": str(mnf_err)}

        except Exception as exc:
            await self.handle_error(exc, interaction, "litert_chat")
            return {"ok": False, "error": str(exc)}

    async def handle_import_instructions(
        self,
        interaction: Any,
        model_name: str = "gemma4-26b"
    ) -> Dict[str, Any]:
        """Provides instructions and commands to import models into LiteRT."""
        try:
            instructions = self.service.get_import_instructions(model_name)
            await self.handle_success(
                interaction,
                data=instructions,
                title=f"📥 LiteRT Import Uputstvo — {model_name}",
                color=0xFBBC05
            )
            return {"ok": True, "instructions": instructions}
        except Exception as exc:
            await self.handle_error(exc, interaction, "litert_import_instructions")
            return {"ok": False, "error": str(exc)}
