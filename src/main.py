"""
main.py — Application Bootstrap & Dependency Injection Root.
============================================================
First import ensures Sentry observability is active.
Initializes Discord bot and registers pure routes.
"""

# FIRST IMPORT per backend-dev-guidelines Section 3
import src.instrument

import sys
import logging
import asyncio
import discord
from discord.ext import commands

from src.config.unified_config import config
from src.routes.slash_routes import register_slash_routes
from src.controllers.nlm_controller import NotebookLMController
from src.controllers.debate_controller import DebateController
from src.controllers.system_controller import SystemController

logger = logging.getLogger("OpenClawBootstrap")


def create_bot() -> commands.Bot:
    """Configures and instantiates the Discord client."""
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True

    bot = commands.Bot(
        command_prefix=config.discord.command_prefix,
        intents=intents
    )

    # Dependency Injection
    nlm_controller = NotebookLMController()
    debate_controller = DebateController()
    system_controller = SystemController()

    # Route registration
    register_slash_routes(
        bot=bot,
        nlm_controller=nlm_controller,
        debate_controller=debate_controller,
        system_controller=system_controller
    )

    @bot.event
    async def on_ready():
        logger.info(f"🤖 Bot prijavljen kao {bot.user} (ID: {bot.user.id})")
        if config.discord.auto_sync_tree:
            try:
                synced = await bot.tree.sync()
                logger.info(f"✅ Sinhronizovano {len(synced)} aplikacionih komandi.")
            except Exception as e:
                logger.error(f"❌ Greška pri sinhronizaciji komandi: {e}")

    return bot


if __name__ == "__main__":
    if not config.discord.token:
        logger.fatal("DISCORD_BOT_TOKEN nije definisan u unified_config!")
        sys.exit(1)

    bot = create_bot()
    bot.run(config.discord.token)
