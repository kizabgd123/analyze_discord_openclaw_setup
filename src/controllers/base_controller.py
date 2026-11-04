"""
base_controller.py — Abstract Base Controller with Standardized Handlers.
========================================================================
Mandatory Controller layer per backend-dev-guidelines:
- All controllers MUST inherit from BaseController.
- Zero raw unhandled responses.
- Explicit error boundaries via `handle_error` and `handle_success`.
- First-class Sentry exception capture on every failure path.
"""

import logging
from typing import Type, TypeVar, Any, Optional, Dict
from pydantic import BaseModel, ValidationError
try:
    import discord
except ImportError:
    discord = None
from src.instrument import capture_exception

logger = logging.getLogger("BaseController")
T = TypeVar("T", bound=BaseModel)


class BaseController:
    """Base Controller establishing standardized response formatting, input parsing, and error capture."""

    def __init__(self, name: str = "BaseController"):
        self.name = name

    def validate_payload(self, schema_cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Validates external input parameters against a Pydantic schema.
        Raises ValidationError with clear contextual details on failure.
        """
        try:
            return schema_cls(**data)
        except ValidationError as val_err:
            logger.warning(f"[{self.name}] Input validation failed: {val_err.errors()}")
            raise val_err

    async def handle_success(
        self,
        interaction_or_ctx: Any,
        data: Any,
        title: str = "✅ Operacija Uspešna",
        color: int = 0x34A853,
        ephemeral: bool = False
    ) -> None:
        """Standardized success responder for Discord interactions or context."""
        if discord is not None:
            embed = discord.Embed(
                title=title,
                description=str(data)[:3900] if data else "Operacija je uspešno izvršena.",
                color=color
            )
            embed.set_footer(text="OpenClaw OS • Production Standard")
            payload = {"embed": embed}
        else:
            payload = {"embed": {"title": title, "description": str(data)[:3900]}}

        if discord and isinstance(interaction_or_ctx, discord.Interaction):
            if interaction_or_ctx.response.is_done():
                await interaction_or_ctx.followup.send(embed=embed, ephemeral=ephemeral)
            else:
                await interaction_or_ctx.response.send_message(embed=embed, ephemeral=ephemeral)
        elif hasattr(interaction_or_ctx, "followup") and hasattr(interaction_or_ctx.followup, "send"):
            await interaction_or_ctx.followup.send(**payload)
        elif hasattr(interaction_or_ctx, "send"):
            await interaction_or_ctx.send(**payload)
        else:
            logger.info(f"[{self.name}] Success: {data}")

    async def handle_error(
        self,
        error: BaseException,
        interaction_or_ctx: Any,
        action_name: str,
        user_friendly_msg: Optional[str] = None
    ) -> None:
        """
        Standardized error handler:
        1. Captures exception to Sentry with context.
        2. Logs structured error trace.
        3. Delivers a clean, non-leaking user-facing error embed.
        """
        context = {
            "controller": self.name,
            "action": action_name,
            "error_type": type(error).__name__
        }
        capture_exception(error, context)

        error_desc = user_friendly_msg or f"Greška tokom izvršavanja `{action_name}`: {str(error)}"
        if discord is not None:
            embed = discord.Embed(
                title=f"❌ Greška [{self.name}]",
                description=f"```{error_desc[:3800]}```",
                color=0xEA4335
            )
            embed.set_footer(text="OpenClaw Observability • Sentry Boundary")
            payload = {"embed": embed}
        else:
            payload = {"embed": {"title": f"❌ Greška [{self.name}]", "description": error_desc[:3800]}}

        try:
            if discord and isinstance(interaction_or_ctx, discord.Interaction):
                if interaction_or_ctx.response.is_done():
                    await interaction_or_ctx.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction_or_ctx.response.send_message(embed=embed, ephemeral=True)
            elif hasattr(interaction_or_ctx, "followup") and hasattr(interaction_or_ctx.followup, "send"):
                await interaction_or_ctx.followup.send(**payload)
            elif hasattr(interaction_or_ctx, "send"):
                await interaction_or_ctx.send(**payload)
        except Exception as send_err:
            logger.error(f"[{self.name}] Failed to dispatch error embed to Discord: {send_err}")
