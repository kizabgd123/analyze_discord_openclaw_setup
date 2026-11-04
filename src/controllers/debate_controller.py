"""
debate_controller.py — Controller for Multi-Agent Debate & ADK Orchestration.
=============================================================================
Inherits from BaseController. Handles dynamic orchestration lifecycle.
"""

from typing import Any, Optional, Dict
try:
    import discord
except ImportError:
    discord = None
from src.controllers.base_controller import BaseController
from src.services.orchestration_service import OrchestrationService
from src.validators.debate_schemas import StartDebateSchema


class DebateController(BaseController):
    """Coordinates multi-agent debate and ADK 2.0 orchestration commands."""

    def __init__(self, service: Optional[OrchestrationService] = None):
        super().__init__(name="DebateController")
        self.service = service or OrchestrationService()

    async def start(
        self,
        interaction_or_ctx: Any,
        topic: str,
        rounds: int = 2,
        custom_notebooks: Optional[Dict[str, str]] = None
    ) -> None:
        """Initiates dynamic ADK 2.0 multi-agent debate."""
        try:
            validated = self.validate_payload(
                StartDebateSchema,
                {"topic": topic, "rounds": rounds, "custom_notebooks": custom_notebooks}
            )

            # Intro confirmation
            intro_text = (
                f"**Tema:** {validated.topic}\n"
                f"**Broj rundi:** {validated.rounds}\n"
                f"**Orkestrator:** Miki Nosonja (Google ADK 2.0 Dynamic Engine)"
            )
            await self.handle_success(
                interaction_or_ctx,
                intro_text,
                title="🎙️ ADK 2.0 Orkestracija Agenata Pokrenuta",
                color=0x9333EA
            )

            # Execution callback for streaming intermediate agent turns to Discord
            channel = getattr(interaction_or_ctx, "channel", None)

            async def on_turn(author: str, text: str):
                if channel and text:
                    embed = discord.Embed(
                        title=f"🤖 {author}",
                        description=text[:3900],
                        color=0x4285F4
                    )
                    embed.set_footer(text="Google ADK 2.0 • Zero Mock")
                    try:
                        await channel.send(embed=embed)
                    except Exception:
                        pass

            # Delegate execution to domain service
            await self.service.execute_task(
                task=validated.topic,
                on_event_callback=on_turn
            )

        except Exception as exc:
            await self.handle_error(exc, interaction_or_ctx, action_name="debate_start")
