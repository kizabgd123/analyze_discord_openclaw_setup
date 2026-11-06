"""
kaggle2_controller.py — Discord Interaction Controller for S6E11 Multi-Agent System.
=====================================================================================
Handles slash commands (/kaggle2 start, /kaggle2 status, /kaggle2 stop) and UI buttons:
  - Strict Admin Authorization from unified_config (fail-closed, no hardcoded fallback).
  - Stop button terminates child runner process cleanly.
  - First submission interactive Confirm button.
  - Generates and uploads view.html attachments to Discord.
"""

import os
import io
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

import discord
from discord import ui

from src.config.unified_config import unified_config
from src.services.kaggle2.agent_team import AgentTeamOrchestrator

logger = logging.getLogger("Kaggle2.Controller")


def check_admin_auth(user_or_interaction) -> bool:
    """Verifies that caller is the configured admin with zero fallback."""
    admin_id = getattr(unified_config.discord, "admin_user_id", None) if unified_config.discord else None
    if admin_id is None:
        logger.warning("Admin authorization failed: unified_config.discord.admin_user_id is unset.")
        return False

    if hasattr(user_or_interaction, "user"):
        caller_id = getattr(user_or_interaction.user, "id", None)
    elif hasattr(user_or_interaction, "author"):
        caller_id = getattr(user_or_interaction.author, "id", None)
    else:
        caller_id = getattr(user_or_interaction, "id", None)

    if caller_id is None or str(caller_id) != str(admin_id):
        logger.warning(f"Admin authorization rejected: caller {caller_id} != configured admin {admin_id}")
        return False

    return True


class Kaggle2ActionView(ui.View):
    """Interactive Discord Action Row for /kaggle2 monitoring and control."""

    def __init__(self, orchestrator: AgentTeamOrchestrator):
        super().__init__(timeout=None)
        self.orchestrator = orchestrator

    @ui.button(label="🛑 Stop Run", style=discord.ButtonStyle.danger, custom_id="kaggle2_stop_run")
    async def stop_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        if not check_admin_auth(interaction):
            await interaction.response.send_message("❌ Pristup odbijen: Niste autorizovani administrator.", ephemeral=True)
            return

        await interaction.response.defer()
        res = await self.orchestrator.stop()
        button.disabled = True
        button.label = "Run Stopped"

        embed = interaction.message.embeds[0] if interaction.message.embeds else discord.Embed(title="Kaggle S6E11 Run")
        embed.color = discord.Color.red()
        embed.add_field(name="Status", value="🛑 Zaustavljeno od strane administratora.", inline=False)
        embed.set_footer(text="Lokalni proces je prekinut. UPOZORENJE: Kaggle CLI ne podržava otkazivanje pokrenutih remote kernela; remote run nastavlja izvršavanje na Kaggle-u do kraja.")

        # Re-attach updated HTML
        html_file = Path(self.orchestrator.html_file)
        discord_file = discord.File(str(html_file), filename=f"dashboard_{self.orchestrator.run_id}.html") if html_file.exists() else None

        await interaction.message.edit(embed=embed, view=self, attachments=[discord_file] if discord_file else [])
        await interaction.followup.send("🛑 Trka je uspešno zaustavljena. Svi lokalni procesi su terminisani. (Kaggle remote kerneli, ukoliko postoje, nastavljaju na Kaggle-u).", ephemeral=True)

    @ui.button(label="📊 Osveži Status", style=discord.ButtonStyle.secondary, custom_id="kaggle2_refresh_status")
    async def refresh_button_callback(self, interaction: discord.Interaction, button: ui.Button):
        if not check_admin_auth(interaction):
            await interaction.response.send_message("❌ Pristup odbijen: Niste autorizovani administrator.", ephemeral=True)
            return

        await interaction.response.defer()
        html_file = Path(self.orchestrator.html_file)
        discord_file = discord.File(str(html_file), filename=f"dashboard_{self.orchestrator.run_id}.html") if html_file.exists() else None
        await interaction.followup.send(f"📊 Dashboard osvežen za run `{self.orchestrator.run_id}`.", file=discord_file, ephemeral=True)


class Kaggle2Controller:
    """Singleton controller managing /kaggle2 workflows."""

    def __init__(self):
        self.active_runs: Dict[str, AgentTeamOrchestrator] = {}

    async def handle_start(self, interaction: discord.Interaction):
        """Entry point for /kaggle2 start slash command."""
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except Exception:
            pass

        if not check_admin_auth(interaction):
            await interaction.followup.send("❌ Pristup odbijen: Niste autorizovani administrator.", ephemeral=True)
            return

        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        orchestrator = AgentTeamOrchestrator(run_id=run_id)
        self.active_runs[run_id] = orchestrator

        # Initialize run
        init_res = await orchestrator.initialize_run()

        embed = discord.Embed(
            title="🚀 Kaggle Playground S6E11: Multi-Agent System Pokrenut",
            description=f"Pokrenut je autonoman tim agenata za **playground-series-s6e11** FROM ZERO.\n"
                        f"• **Run ID:** `{run_id}`\n"
                        f"• **CV Strategija:** `{orchestrator.state.get('folds_info')}`\n"
                        f"• **Izvori u svesci:** `{init_res.get('sources_count')} izvora`\n"
                        f"• **Hard Cap predaja:** 5 po run-u (0 poslato u ovom probnom ciklusu)\n",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Triada agenata", value="• **Strategist:** Hipoteze i NLM istraživanje\n• **Engineer:** Implementacija koda\n• **Skeptic:** Zabrana leakage-a i verifikacija metrike", inline=False)
        embed.set_footer(text="Prva predaja zahteva Confirm dugme. Dashboard se osvežava posle svakog kruga.")

        html_file = Path(orchestrator.html_file)
        discord_file = discord.File(str(html_file), filename=f"dashboard_{run_id}.html") if html_file.exists() else None

        view = Kaggle2ActionView(orchestrator)
        await interaction.followup.send(embed=embed, view=view, file=discord_file)

        # Launch autonomous cycle in background
        asyncio.create_task(self._run_cycle(orchestrator, interaction.channel))

    async def handle_start_prefix(self, ctx):
        """Entry point for !kaggle2 start prefix command."""
        if not check_admin_auth(ctx):
            await ctx.send("❌ Pristup odbijen: Niste autorizovani administrator.")
            return

        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        orchestrator = AgentTeamOrchestrator(run_id=run_id)
        self.active_runs[run_id] = orchestrator

        # Initialize run
        await ctx.send(f"⏳ Inicijalizujem Kaggle S6E11 V2 autonomni tim agenata (Run ID: `{run_id}`)...")
        init_res = await orchestrator.initialize_run()

        embed = discord.Embed(
            title="🚀 Kaggle Playground S6E11: Multi-Agent System Pokrenut",
            description=f"Pokrenut je autonoman tim agenata za **playground-series-s6e11** FROM ZERO.\n"
                        f"• **Run ID:** `{run_id}`\n"
                        f"• **CV Strategija:** `{orchestrator.state.get('folds_info')}`\n"
                        f"• **Izvori u svesci:** `{init_res.get('sources_count')} izvora`\n"
                        f"• **Hard Cap predaja:** 5 po run-u (0 poslato u ovom probnom ciklusu)\n",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Triada agenata", value="• **Strategist:** Hipoteze i NLM istraživanje\n• **Engineer:** Implementacija koda\n• **Skeptic:** Zabrana leakage-a i verifikacija metrike", inline=False)
        embed.set_footer(text="Prva predaja zahteva Confirm dugme. Dashboard se osvežava posle svakog kruga.")

        html_file = Path(orchestrator.html_file)
        discord_file = discord.File(str(html_file), filename=f"dashboard_{run_id}.html") if html_file.exists() else None

        view = Kaggle2ActionView(orchestrator)
        await ctx.send(embed=embed, view=view, file=discord_file)

        # Launch autonomous cycle in background
        asyncio.create_task(self._run_cycle(orchestrator, ctx.channel))

    async def _run_cycle(self, orchestrator: AgentTeamOrchestrator, channel: Optional[discord.abc.Messageable]):
        try:
            res = await orchestrator.run_autonomous_cycle(max_experiments=2, timeout_per_exp=1200)
            if channel:
                html_file = Path(orchestrator.html_file)
                discord_file = discord.File(str(html_file), filename=f"dashboard_{orchestrator.run_id}_final.html") if html_file.exists() else None
                embed = discord.Embed(
                    title=f"🏁 Kaggle S6E11 Ciklus Završen — Run {orchestrator.run_id}",
                    description=f"Autonomni probni ciklus je uspešno završen.\n"
                                f"• **Izvršeno eksperimenata:** {res.get('experiments_run', 0)}\n"
                                f"• **Lekcije:** Dodate kao novi izvori u NotebookLM svesku\n"
                                f"• **Predaje na Kaggle:** 0 (Nema predaje u ovom probnom run-u)\n",
                    color=discord.Color.blue(),
                    timestamp=datetime.now(timezone.utc)
                )
                for exp in orchestrator.state.get("experiments", []):
                    cv_str = f"{exp.get('cv_score'):.5f}" if exp.get('cv_score') is not None else "FAILED"
                    embed.add_field(name=f"Exp #{exp.get('exp_no')}", value=f"Status: {exp.get('status')} | CV ROC-AUC: `{cv_str}`", inline=False)
                await channel.send(embed=embed, file=discord_file)
        except Exception as exc:
            logger.error(f"Error in autonomous cycle: {exc}", exc_info=True)
            if channel:
                await channel.send(f"❌ Greška u izvršavanju ciklusa agenata: `{exc}`")


kaggle2_controller = Kaggle2Controller()
