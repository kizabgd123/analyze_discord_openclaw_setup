"""
slash_routes.py — Pure Route Definitions for Discord Application Commands.
==========================================================================
Strictly adheres to backend-dev-guidelines Doctrine:
- "Routes Only Route": Contains ZERO business logic or database queries.
- Each handler strictly delegates to the respective Controller.
"""

from typing import Optional
import discord
from discord import app_commands
from src.controllers.nlm_controller import NotebookLMController
from src.controllers.debate_controller import DebateController
from src.controllers.system_controller import SystemController


def register_slash_routes(
    bot: discord.Client,
    nlm_controller: Optional[NotebookLMController] = None,
    debate_controller: Optional[DebateController] = None,
    system_controller: Optional[SystemController] = None,
) -> None:
    """Registers all clean application commands on the bot's command tree."""
    nlm_ctrl = nlm_controller or NotebookLMController()
    debate_ctrl = debate_controller or DebateController()
    sys_ctrl = system_controller or SystemController()

    # ── 1. NotebookLM Routes ──

    @bot.tree.command(name="ask", description="Postavi direktno pitanje u Google NotebookLM svesku")
    @app_commands.describe(
        pitanje="Pitanje koje želiš da postaviš na osnovu svojih izvora",
        sveska="Opcioni ID specifične sveske"
    )
    async def ask_route(interaction: discord.Interaction, pitanje: str, sveska: Optional[str] = None):
        await interaction.response.defer()
        await nlm_ctrl.ask(interaction, query=pitanje, notebook_id=sveska)

    @bot.tree.command(name="notebooks", description="Prikaži dostupne Google NotebookLM sveske")
    async def notebooks_route(interaction: discord.Interaction):
        await interaction.response.defer()
        await nlm_ctrl.list_notebooks(interaction)

    @bot.tree.command(name="note", description="Dodaj novu belešku u svesku")
    @app_commands.describe(tekst="Sadržaj beleške", naslov="Naslov beleške")
    async def note_route(interaction: discord.Interaction, tekst: str, naslov: Optional[str] = None):
        await interaction.response.defer()
        await nlm_ctrl.add_note(interaction, text=tekst, title=naslov)

    @bot.tree.command(name="addurl", description="Dodaj URL ili YouTube video kao izvor")
    @app_commands.describe(url="Veb URL ili YouTube link")
    async def addurl_route(interaction: discord.Interaction, url: str):
        await interaction.response.defer()
        await nlm_ctrl.add_url(interaction, url=url)

    # ── 2. Debate & ADK Orchestration Routes ──

    debate_group = app_commands.Group(
        name="debate",
        description="Komande za Google ADK 2.0 dinamičku orkestraciju agenata"
    )

    @debate_group.command(name="start", description="Pokreni orkestraciju agenata")
    @app_commands.describe(tema="Glavna tema ili zadatak za tim agenata", runde="Broj rundi (1-5)")
    async def debate_start_route(interaction: discord.Interaction, tema: str, runde: Optional[int] = 2):
        await interaction.response.defer()
        await debate_ctrl.start(interaction, topic=tema, rounds=runde or 2)

    bot.tree.add_command(debate_group)

    # ── 3. System & Safety Routes ──

    @bot.tree.command(name="status", description="Proveri zdravlje sistema, NLM CLI i JudgeGuard")
    async def status_route(interaction: discord.Interaction):
        await interaction.response.defer()
        await sys_ctrl.get_status(interaction)

    @bot.tree.command(name="sh", description="Izvrši shell komandu uz JudgeGuard autorizaciju")
    @app_commands.describe(komanda="Bash komanda za pokretanje")
    async def sh_route(interaction: discord.Interaction, komanda: str):
        await interaction.response.defer()
        await sys_ctrl.execute_command(interaction, command=komanda)
