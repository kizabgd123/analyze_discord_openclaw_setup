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
from src.controllers.litert_controller import LiteRTController


def register_slash_routes(
    bot: discord.Client,
    nlm_controller: Optional[NotebookLMController] = None,
    debate_controller: Optional[DebateController] = None,
    system_controller: Optional[SystemController] = None,
    litert_controller: Optional[LiteRTController] = None,
) -> None:
    """Registers all clean application commands on the bot's command tree."""
    nlm_ctrl = nlm_controller or NotebookLMController()
    debate_ctrl = debate_controller or DebateController()
    sys_ctrl = system_controller or SystemController()
    litert_ctrl = litert_controller or LiteRTController()

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

    # ── 4. On-Device LiteRT & Local Model Routes ──

    litert_group = app_commands.Group(
        name="litert",
        description="⚡ On-Device Google AI Edge LiteRT i lokalni agenti bez API ključa"
    )

    @litert_group.command(name="chat", description="Pokreni lokalnog agenta sa .litertlm ili lokalnim modelom")
    @app_commands.describe(
        upit="Zadatak ili pitanje za lokalnog agenta",
        instrukcije="Opcione sistemske instrukcije",
        eksterni="Koristi eksterni OpenAI-kompatibilni server (Ollama / LM Studio)"
    )
    async def litert_chat_route(
        interaction: discord.Interaction,
        upit: str,
        instrukcije: Optional[str] = None,
        eksterni: Optional[bool] = False
    ):
        await interaction.response.defer()
        await litert_ctrl.handle_chat(
            interaction,
            prompt=upit,
            system_instructions=instrukcije,
            use_external_server=bool(eksterni)
        )

    @litert_group.command(name="status", description="Status lokalnog LiteRT okruženja, modela i hardvera")
    async def litert_status_route(interaction: discord.Interaction):
        await interaction.response.defer()
        await litert_ctrl.handle_status(interaction)

    @litert_group.command(name="import_info", description="Uputstvo za preuzimanje i import Gemma 4 modela")
    @app_commands.describe(model_id="Identifikator modela (podrazumevano: gemma4-26b)")
    async def litert_import_route(interaction: discord.Interaction, model_id: Optional[str] = "gemma4-26b"):
        await interaction.response.defer()
        await litert_ctrl.handle_import_instructions(interaction, model_name=model_id or "gemma4-26b")

    bot.tree.add_command(litert_group)
