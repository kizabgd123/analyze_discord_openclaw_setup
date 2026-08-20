#!/usr/bin/env python3
"""
OpenClaw Discord Bot with Direct Google NotebookLM Integration
Zero mock, zero simulation - 100% real Google NotebookLM API via `nlm` CLI.
Supports Native Discord Slash Commands (/ask, /notebooks, /use, /sources, /note, etc.),
Dynamic Autocomplete, Interactive Select Menus, Pop-up Modals, and Action Buttons.
"""

import os
import sys
import asyncio
import logging
import json
import re
import shutil
from typing import Optional, Dict, Any, List

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

# ── Antigravity 2.0 cognitive modules ──────────────────────────────────────
try:
    from brain_core import BrainCore
    from judge_guard import JudgeGuard
    _BRAIN_AVAILABLE = True
except ImportError as _brain_import_err:
    _BRAIN_AVAILABLE = False
    logging.getLogger("DiscordNotebookLM").warning(
        f"BrainCore/JudgeGuard not available: {_brain_import_err}"
    )

# ── 1. CONFIGURATION & STARTUP VALIDATION ──
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DEFAULT_NOTEBOOK_ID = os.getenv("NLM_NOTEBOOK_ID", "bf77f7c8-ae62-4eac-b6e5-a17ed6252676")
NLM_BIN = shutil.which("nlm") or "/home/kizamladjanijebac/.local/bin/nlm"
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "MEMORY.md")
SOUL_FILE = os.path.join(os.path.dirname(__file__), "SOUL.md")
HEARTBEAT_FILE = os.path.join(os.path.dirname(__file__), "HEARTBEAT.md")

if not TOKEN:
    print("❌ FATAL: DISCORD_BOT_TOKEN nije postavljen u .env")
    sys.exit(1)

# ── 2. LOGGING ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("DiscordNotebookLM")

# ── 3. NOTEBOOKLM ENGINE (REAL GOOGLE API INTEGRATION VIA NLM CLI) ──
class NotebookLMEngine:
    """
    Direct client for Google NotebookLM using the official unified `nlm` CLI.
    Zero mock, zero simulation - connects directly to Google's production endpoints.
    """
    def __init__(self, binary_path: str = NLM_BIN):
        self.binary_path = binary_path
        self.notebook_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = asyncio.Lock()

    def _get_auth_env(self) -> Dict[str, str]:
        """Loads and refreshes Google auth tokens and cookies from ~/.nlm/env."""
        env = os.environ.copy()
        nlm_env_file = os.path.expanduser("~/.nlm/env")
        if os.path.exists(nlm_env_file):
            try:
                with open(nlm_env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("export "):
                            line = line[7:]
                        if "=" in line:
                            k, v = line.split("=", 1)
                            env[k] = v.strip('"\'')
            except Exception as e:
                logger.warning(f"Greška pri čitanju ~/.nlm/env: {e}")
        return env

    async def check_auth(self) -> Dict[str, Any]:
        """Proverava status autentifikacije i verziju NLM CLI-ja."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self.binary_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            version = stdout.decode().strip()
            
            # Test simple list
            nbs = await self.list_notebooks(limit=3)
            return {
                "ok": True,
                "version": version,
                "notebook_count": len(nbs),
                "binary": self.binary_path
            }
        except Exception as e:
            return {"ok": False, "error": str(e), "binary": self.binary_path}

    async def list_notebooks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Dohvata listu svih pravih NotebookLM svezaka korisnika direktno sa Google-a."""
        env = self._get_auth_env()
        try:
            proc = await asyncio.create_subprocess_exec(
                self.binary_path, "list", "notebooks", "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            if proc.returncode != 0:
                logger.error(f"NLM list error: {stderr.decode()}")
                return []
            
            data = json.loads(stdout.decode())
            if isinstance(data, list):
                async with self._cache_lock:
                    for nb in data:
                        if "id" in nb:
                            self.notebook_cache[nb["id"]] = nb
                return data[:limit]
            return []
        except Exception as e:
            logger.error(f"Izuzetak u list_notebooks: {e}")
            return []

    async def list_sources(self, notebook_id: str) -> List[Dict[str, Any]]:
        """Dohvata listu izvora unutar date sveske."""
        env = self._get_auth_env()
        try:
            proc = await asyncio.create_subprocess_exec(
                self.binary_path, "list", "sources", notebook_id, "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            if proc.returncode != 0:
                logger.error(f"NLM list sources error: {stderr.decode()}")
                return []
            data = json.loads(stdout.decode())
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"Izuzetak u list_sources: {e}")
            return []

    async def query(
        self,
        notebook_id: str,
        question: str,
        conversation_id: Optional[str] = None,
        timeout: float = 120.0
    ) -> Dict[str, Any]:
        """
        Šalje upit direktno u Google NotebookLM i vraća tačan odgovor,
        reference i konverzacijski ID za nastavak razgovora.
        """
        env = self._get_auth_env()
        cmd = [self.binary_path, "query", "notebook", "--json"]
        if conversation_id:
            cmd.extend(["--conversation-id", conversation_id])
        cmd.extend([notebook_id, question])

        logger.info(f"[NLM Query] Notebook: {notebook_id[:8]} | Conv: {conversation_id or 'NEW'} | Q: {question[:60]}...")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            
            raw_out = stdout.decode("utf-8", errors="replace").strip()
            raw_err = stderr.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                logger.error(f"NLM Query failed (code {proc.returncode}): {raw_err or raw_out}")
                try:
                    err_json = json.loads(raw_out or raw_err)
                    return {"success": False, "error": err_json.get("error", "Nepoznata greška sa NotebookLM API-jem.")}
                except Exception:
                    pass
                return {"success": False, "error": f"NotebookLM API greška: {raw_err[:300] or raw_out[:300]}"}

            data = json.loads(raw_out)
            answer = data.get("answer", "").strip()
            references = data.get("references", [])
            new_conv_id = data.get("conversation_id")

            if not answer and not references:
                return {"success": False, "error": "NotebookLM je vratio prazan odgovor."}

            return {
                "success": True,
                "answer": answer,
                "references": references,
                "conversation_id": new_conv_id
            }

        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return {"success": False, "error": "⏱️ Timeout: Google NotebookLM nije odgovorio u roku od 120s."}
        except json.JSONDecodeError:
            return {"success": False, "error": f"Nevalidan JSON odgovor: {raw_out[:200]}"}
        except Exception as e:
            logger.exception("Neočekivana greška u query()")
            return {"success": False, "error": f"Lokalna greška: {str(e)}"}

    async def add_note(self, notebook_id: str, content: str, title: Optional[str] = None) -> Dict[str, Any]:
        """Kreira novu belešku u svesci."""
        env = self._get_auth_env()
        cmd = [self.binary_path, "note", "create", notebook_id, "--content", content]
        if title:
            cmd.extend(["--title", title])
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            if proc.returncode == 0:
                return {"success": True, "output": stdout.decode().strip()}
            return {"success": False, "error": stderr.decode().strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def add_source_url(self, notebook_id: str, url: str) -> Dict[str, Any]:
        """Dodaje URL kao izvor u svesku."""
        env = self._get_auth_env()
        cmd = [self.binary_path, "source", "add", notebook_id, "--url", url]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
            if proc.returncode == 0:
                return {"success": True, "output": stdout.decode().strip()}
            return {"success": False, "error": stderr.decode().strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_cached_title(self, notebook_id: str) -> str:
        """Vraća keširano ime beležnice ili skraćeni ID."""
        if notebook_id in self.notebook_cache:
            title = self.notebook_cache[notebook_id].get("title")
            if title:
                return title
        return notebook_id[:8]

# ── 4. STATE & HELPERS ──
nlm = NotebookLMEngine()

# Antigravity 2.0 — cognitive singletons (loaded after .env is applied)
if _BRAIN_AVAILABLE:
    _JUDGE_SECRET = os.getenv("JUDGE_HMAC_SECRET", "openclaw-dev-secret")
    brain = BrainCore(default_notebook_id=DEFAULT_NOTEBOOK_ID)
    judge = JudgeGuard(secret=_JUDGE_SECRET)
    logger.info("✅ BrainCore + JudgeGuard singletons aktivni")
else:
    brain = None  # type: ignore
    judge = None  # type: ignore

# Per-channel active notebook and conversation
channel_notebooks: Dict[int, str] = {}
channel_conversations: Dict[int, str] = {}
cached_notebook_list: List[Dict[str, Any]] = []

def get_channel_notebook(channel_id: int) -> str:
    """Vraća aktivnu svesku za kanal ili podrazumevanu."""
    return channel_notebooks.get(channel_id, DEFAULT_NOTEBOOK_ID)

def split_text_for_discord(text: str, max_chunk_size: int = 1850) -> List[str]:
    """Pametno deli dugačak tekst u više poruka bez sečenja reči ili blokova."""
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    current_chunk = ""
    paragraphs = text.split("\n\n")
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_chunk_size:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
            
            if len(para) > max_chunk_size:
                lines = para.split("\n")
                for line in lines:
                    if len(current_chunk) + len(line) + 1 <= max_chunk_size:
                        current_chunk += ("\n" if current_chunk else "") + line
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                            current_chunk = ""
                        while len(line) > max_chunk_size:
                            chunks.append(line[:max_chunk_size])
                            line = line[max_chunk_size:]
                        current_chunk = line
            else:
                current_chunk = para
                
    if current_chunk:
        chunks.append(current_chunk)
    return chunks

# ── 5. UI COMPONENTS: MODALS, SELECTS & VIEWS ──

class AddNoteModal(discord.ui.Modal, title="📝 Nova Beleška u NotebookLM"):
    note_title = discord.ui.TextInput(
        label="Naslov beleške (opciono)",
        placeholder="npr. Ključna ideja ili zaključak sastanka...",
        required=False,
        max_length=100
    )
    note_content = discord.ui.TextInput(
        label="Sadržaj beleške",
        style=discord.TextStyle.paragraph,
        placeholder="Unesi tekst beleške koji će biti sačuvan i indeksiran u Google NotebookLM...",
        required=True,
        max_length=2000
    )

    def __init__(self, notebook_id: str):
        super().__init__()
        self.notebook_id = notebook_id

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        title = self.note_title.value.strip() or f"Discord Note from {interaction.user.name}"
        content = self.note_content.value.strip()
        nb_title = nlm.get_cached_title(self.notebook_id)

        res = await nlm.add_note(self.notebook_id, content=content, title=title)
        if res.get("success"):
            embed = discord.Embed(
                title="✅ Beleška Uspešno Sačuvana u Google NotebookLM!",
                description=f"**Sveska:** {nb_title}\n**Naslov:** {title}\n\n```\n{content[:500]}\n```",
                color=0x34A853
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Greška pri upisu beleške: {res.get('error')}", ephemeral=True)


class NotebookSelectDropdown(discord.ui.Select):
    def __init__(self, notebooks: List[Dict[str, Any]], current_nb_id: str):
        options = []
        for nb in notebooks[:25]:
            nb_id = nb.get("id", "")
            title = (nb.get("title") or "Beležnica bez naslova")[:80]
            src_count = nb.get("source_count", 0)
            is_default = (nb_id == current_nb_id)
            options.append(
                discord.SelectOption(
                    label=title,
                    value=nb_id,
                    description=f"{src_count} izvora | ID: {nb_id[:8]}...",
                    emoji="📖" if not is_default else "👉",
                    default=is_default
                )
            )
        super().__init__(
            placeholder="🔍 Izaberi Google NotebookLM svesku...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        selected_id = self.values[0]
        channel_notebooks[interaction.channel_id] = selected_id
        channel_conversations.pop(interaction.channel_id, None)
        title = nlm.get_cached_title(selected_id)

        embed = discord.Embed(
            title="✅ Aktivna Sveska je Promenjena!",
            description=f"Izabrana je: **{title}** (`{selected_id}`)\nRazgovor je resetovan na novu temu.",
            color=0x4285F4
        )
        await interaction.response.send_message(embed=embed)


class NotebookSelectView(discord.ui.View):
    def __init__(self, notebooks: List[Dict[str, Any]], current_nb_id: str, page: int = 0):
        super().__init__(timeout=180)
        self.notebooks = notebooks
        self.current_nb_id = current_nb_id
        self.page = page
        self.page_size = 25
        self.max_pages = max(1, (len(notebooks) + self.page_size - 1) // self.page_size)

        start = self.page * self.page_size
        end = start + self.page_size
        page_nbs = notebooks[start:end]

        self.add_item(NotebookSelectDropdown(page_nbs, current_nb_id))

        if self.max_pages > 1:
            self.prev_button.disabled = (self.page == 0)
            self.next_button.disabled = (self.page >= self.max_pages - 1)
        else:
            self.remove_item(self.prev_button)
            self.remove_item(self.next_button)

    @discord.ui.button(label="⬅️ Prethodna", style=discord.ButtonStyle.secondary, row=1)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            new_view = NotebookSelectView(self.notebooks, self.current_nb_id, self.page)
            embed = self.build_embed()
            await interaction.response.edit_message(embed=embed, view=new_view)

    @discord.ui.button(label="➡️ Sledeća", style=discord.ButtonStyle.secondary, row=1)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_pages - 1:
            self.page += 1
            new_view = NotebookSelectView(self.notebooks, self.current_nb_id, self.page)
            embed = self.build_embed()
            await interaction.response.edit_message(embed=embed, view=new_view)

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="📚 Izbor Google NotebookLM Sveske",
            description=(
                f"Ukupno pronađeno: **{len(self.notebooks)}** svezaka (Stranica {self.page + 1}/{self.max_pages})\n"
                "Izaberi svesku iz padajućeg menija ispod:"
            ),
            color=0x4285F4
        )
        return embed


class NotebookActionRow(discord.ui.View):
    """Interaktivna traka sa dugmićima koja ide ispod svakog odgovora od bota."""
    def __init__(self, notebook_id: str):
        super().__init__(timeout=300)
        self.notebook_id = notebook_id

    @discord.ui.button(label="Novi Razgovor", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def reset_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel_conversations.pop(interaction.channel_id, None)
        title = nlm.get_cached_title(self.notebook_id)
        await interaction.response.send_message(
            f"🔄 **Konverzacija je resetovana!** Sledeće pitanje počinje novu temu u svesci **{title}**.",
            ephemeral=True
        )

    @discord.ui.button(label="Promeni Svesku", style=discord.ButtonStyle.primary, emoji="📚")
    async def change_nb_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        nbs = cached_notebook_list or await nlm.list_notebooks(limit=50)
        current_nb = get_channel_notebook(interaction.channel_id)
        view = NotebookSelectView(nbs, current_nb)
        embed = view.build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Izvori", style=discord.ButtonStyle.secondary, emoji="📂")
    async def sources_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(thinking=True, ephemeral=True)
        title = nlm.get_cached_title(self.notebook_id)
        sources = await nlm.list_sources(self.notebook_id)
        if not sources:
            await interaction.followup.send(f"📂 Sveska **{title}** nema dodatih izvora.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📂 Izvori u svesci: {title}",
            description=f"Ukupno: **{len(sources)}** izvora/fajlova",
            color=0xFBBC05
        )
        lines = [f"**{i}.** {s.get('title', 'Dokument')} `[{s.get('type', 'file')}]`" for i, s in enumerate(sources[:15], 1)]
        embed.description += "\n\n" + "\n".join(lines)
        if len(sources) > 15:
            embed.description += f"\n\n*...i još {len(sources) - 15} izvora.*"
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Dodaj Belešku", style=discord.ButtonStyle.success, emoji="📝")
    async def add_note_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AddNoteModal(self.notebook_id)
        await interaction.response.send_modal(modal)


class ExecApprovalView(discord.ui.View):
    def __init__(self, command: str, user_id: int):
        super().__init__(timeout=60)
        self.command = command
        self.user_id = user_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Samo autor komande može da je odobri.", ephemeral=True)
            return
            
        await interaction.response.edit_message(content=f"✅ **Odobreno.** Izvršavam: `{self.command}`...", view=None)
        
        try:
            proc = await asyncio.create_subprocess_shell(
                self.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/home/kizamladjanijebac/Desktop/openclaw"
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            output = (stdout or stderr).decode("utf-8")
            
            result_msg = f"🖥️ **Rezultat komande:**\n```\n{output[:1900] or '(Prazan izlaz)'}\n```"
            await interaction.followup.send(result_msg)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Greška pri izvršavanju: {e}")

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, emoji="❌")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Samo ti možeš da otkažeš komandu.", ephemeral=True)
            return
        await interaction.response.edit_message(content="❌ Komanda odbijena.", view=None)

# ── 6. DISCORD BOT SETUP & AUTOCOMPLETE ──
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

async def notebook_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """Dinamički autocomplete koji filtrira Google NotebookLM sveske dok korisnik kuca."""
    global cached_notebook_list
    nbs = cached_notebook_list
    if not nbs:
        nbs = await nlm.list_notebooks(limit=50)
        cached_notebook_list = nbs

    choices = []
    current_lower = current.lower().strip()

    for nb in nbs:
        title = nb.get("title") or "Beležnica bez naslova"
        nb_id = nb.get("id", "")
        src_cnt = nb.get("source_count", 0)
        display = f"{title[:75]} ({src_cnt} izvora)"

        if not current_lower or current_lower in title.lower() or current_lower in nb_id.lower():
            choices.append(app_commands.Choice(name=display, value=nb_id))
            if len(choices) >= 25:
                break
    return choices

# ── 7. EVENT HANDLERS ──
@bot.event
async def on_ready():
    global cached_notebook_list
    logger.info(f"✅ Discord Bot [{bot.user}] je uspešno ulogovan!")
    logger.info(f"📚 Podrazumevana Google NotebookLM sveska: {DEFAULT_NOTEBOOK_ID}")
    
    # Pre-cache notebooks
    cached_notebook_list = await nlm.list_notebooks(limit=50)
    logger.info(f"Keširano {len(cached_notebook_list)} NotebookLM svezaka.")

    # Sinhronizacija Slash komandi sa Discord Gateway-om
    try:
        synced = await bot.tree.sync()
        logger.info(f"⚡ Sinhronizovano {len(synced)} Slash komandi (Application Commands)!")
    except Exception as e:
        logger.error(f"Greška pri sinhronizaciji slash komandi: {e}")

    # Postavi status bota
    default_title = nlm.get_cached_title(DEFAULT_NOTEBOOK_ID)
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=f"NotebookLM: {default_title[:25]}"
        )
    )

    if not heartbeat_task.is_running():
        heartbeat_task.start()

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if message.content.strip().startswith("!"):
        await bot.process_commands(message)
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mentioned = bot.user in message.mentions or f"<@{bot.user.id}>" in message.content

    if is_dm or is_mentioned:
        clean_content = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        
        if not clean_content:
            active_nb = get_channel_notebook(message.channel.id)
            title = nlm.get_cached_title(active_nb)
            embed = discord.Embed(
                title="🧠 Google NotebookLM Bot je spreman!",
                description=(
                    f"**Aktivna sveska:** {title} (`{active_nb}`)\n\n"
                    "Postavi mi pitanje direktno ili koristi Slash komande (`/ask`, `/notebooks`, `/help`)."
                ),
                color=0x4285F4
            )
            view = NotebookActionRow(active_nb)
            await message.reply(embed=embed, view=view)
            return

        await execute_notebook_chat(message, clean_content)

# ── 8. CHAT EXECUTION LOGIC ──
async def execute_notebook_chat(message: discord.Message, prompt: str):
    channel_id = message.channel.id
    active_nb = get_channel_notebook(channel_id)
    conv_id = channel_conversations.get(channel_id)
    nb_title = nlm.get_cached_title(active_nb)

    logger.info(f"[{message.author.name}] Chatting in '{nb_title}' (conv={conv_id}): {prompt[:50]}...")

    async with message.channel.typing():
        result = await nlm.query(
            notebook_id=active_nb,
            question=prompt,
            conversation_id=conv_id
        )

    if not result.get("success"):
        err_msg = result.get("error", "Nepoznata greška.")
        await message.reply(f"❌ **Greška sa Google NotebookLM-om:**\n{err_msg}")
        return

    if result.get("conversation_id"):
        channel_conversations[channel_id] = result["conversation_id"]

    answer_text = result.get("answer", "")
    references = result.get("references", [])

    chunks = split_text_for_discord(answer_text, max_chunk_size=1800)
    view = NotebookActionRow(active_nb)
    
    for idx, chunk in enumerate(chunks):
        if idx == len(chunks) - 1:
            footer = f"\n\n*📚 NotebookLM: {nb_title}*"
            if references:
                footer += f" • {len(references)} izvora citirano"
            chunk += footer

        if idx == 0:
            if len(chunks) == 1:
                await message.reply(chunk, view=view)
            else:
                await message.reply(chunk)
        elif idx == len(chunks) - 1:
            await message.channel.send(chunk, view=view)
        else:
            await message.channel.send(chunk)

# ── 9. NATIVE DISCORD SLASH COMMANDS (APPLICATION COMMANDS) ──

@bot.tree.command(name="ask", description="Postavi direktno pitanje u aktivnu Google NotebookLM svesku")
@app_commands.describe(pitanje="Pitanje koje želiš da postaviš na osnovu svojih izvora")
async def ask_slash(interaction: discord.Interaction, pitanje: str):
    await interaction.response.defer(thinking=True)
    channel_id = interaction.channel_id
    active_nb = get_channel_notebook(channel_id)
    conv_id = channel_conversations.get(channel_id)
    nb_title = nlm.get_cached_title(active_nb)

    result = await nlm.query(
        notebook_id=active_nb,
        question=pitanje,
        conversation_id=conv_id
    )

    if not result.get("success"):
        err_msg = result.get("error", "Nepoznata greška.")
        await interaction.followup.send(f"❌ **Greška sa Google NotebookLM-om:**\n{err_msg}")
        return

    if result.get("conversation_id"):
        channel_conversations[channel_id] = result["conversation_id"]

    answer_text = result.get("answer", "")
    references = result.get("references", [])
    chunks = split_text_for_discord(answer_text, max_chunk_size=1800)
    view = NotebookActionRow(active_nb)

    for idx, chunk in enumerate(chunks):
        if idx == len(chunks) - 1:
            footer = f"\n\n*📚 NotebookLM: {nb_title}*"
            if references:
                footer += f" • {len(references)} izvora citirano"
            chunk += footer

        if idx == 0:
            if len(chunks) == 1:
                await interaction.followup.send(chunk, view=view)
            else:
                await interaction.followup.send(chunk)
        elif idx == len(chunks) - 1:
            await interaction.channel.send(chunk, view=view)
        else:
            await interaction.channel.send(chunk)


@bot.tree.command(name="notebooks", description="Prikaži sve tvoje Google NotebookLM sveske sa interaktivnim menijem")
async def notebooks_slash(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    global cached_notebook_list
    cached_notebook_list = await nlm.list_notebooks(limit=50)

    if not cached_notebook_list:
        await interaction.followup.send("❌ Nije pronađena nijedna sveska ili je došlo do greške sa autentifikacijom.")
        return

    current_nb = get_channel_notebook(interaction.channel_id)
    view = NotebookSelectView(cached_notebook_list, current_nb)
    embed = view.build_embed()
    await interaction.followup.send(embed=embed, view=view)


@bot.tree.command(name="use", description="Izaberi aktivnu svesku za ovaj kanal")
@app_commands.describe(sveska="Pretraži i izaberi svesku iz padajuće liste")
@app_commands.autocomplete(sveska=notebook_autocomplete)
async def use_slash(interaction: discord.Interaction, sveska: str):
    global cached_notebook_list
    selected_nb = None

    if not cached_notebook_list:
        cached_notebook_list = await nlm.list_notebooks(limit=50)

    # 1. Proveri po ID-ju
    for nb in cached_notebook_list:
        if sveska.lower() in nb.get("id", "").lower():
            selected_nb = nb
            break

    # 2. Proveri po nazivu
    if not selected_nb:
        for nb in cached_notebook_list:
            if sveska.lower() in nb.get("title", "").lower():
                selected_nb = nb
                break

    if not selected_nb:
        # Možda je direktan UUID koji nije u prvih 50
        selected_nb = {"id": sveska, "title": sveska[:8], "source_count": "?"}

    nb_id = selected_nb["id"]
    nb_title = selected_nb.get("title") or nb_id
    
    channel_notebooks[interaction.channel_id] = nb_id
    channel_conversations.pop(interaction.channel_id, None)

    embed = discord.Embed(
        title="✅ Aktivna Google NotebookLM Sveska je Promenjena!",
        color=0x34A853
    )
    embed.add_field(name="📖 Naslov", value=f"**{nb_title}**", inline=False)
    embed.add_field(name="🆔 Sveska ID", value=f"`{nb_id}`", inline=True)
    embed.add_field(name="📊 Broj Izvora", value=f"`{selected_nb.get('source_count', 0)}`", inline=True)
    embed.set_footer(text="Konverzacijska nit je resetovana na novu temu.")

    view = NotebookActionRow(nb_id)
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="sources", description="Prikaži sve izvore (dokumente/linkove) u svesci")
@app_commands.describe(sveska="Opciono izaberi specifičnu svesku (podrazumevano: aktivna sveska)")
@app_commands.autocomplete(sveska=notebook_autocomplete)
async def sources_slash(interaction: discord.Interaction, sveska: Optional[str] = None):
    await interaction.response.defer(thinking=True)
    nb_id = sveska or get_channel_notebook(interaction.channel_id)
    title = nlm.get_cached_title(nb_id)

    sources = await nlm.list_sources(nb_id)
    if not sources:
        await interaction.followup.send(f"📂 Sveska **{title}** nema dodatih izvora ili je došlo do greške.")
        return

    embed = discord.Embed(
        title=f"📂 Izvori u svesci: {title}",
        description=f"Ukupno dokumenata/izvora: **{len(sources)}**",
        color=0xFBBC05
    )

    lines = [f"**{i}.** {s.get('title', 'Dokument')} `[{s.get('type', 'file')}]`" for i, s in enumerate(sources[:20], 1)]
    embed.description += "\n\n" + "\n".join(lines)
    if len(sources) > 20:
        embed.description += f"\n\n*...i još {len(sources) - 20} izvora.*"

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="note", description="Dodaj novu belešku direktno u svesku")
@app_commands.describe(tekst="Sadržaj beleške (ostavi prazno da otvoriš prozor za unos)", naslov="Naslov beleške (opciono)")
async def note_slash(interaction: discord.Interaction, tekst: Optional[str] = None, naslov: Optional[str] = None):
    nb_id = get_channel_notebook(interaction.channel_id)
    
    if not tekst:
        modal = AddNoteModal(nb_id)
        await interaction.response.send_modal(modal)
        return

    await interaction.response.defer(thinking=True)
    title = naslov or f"Discord Note by {interaction.user.name}"
    res = await nlm.add_note(nb_id, content=tekst, title=title)
    nb_title = nlm.get_cached_title(nb_id)

    if res.get("success"):
        embed = discord.Embed(
            title="✅ Nova Beleška je Uspešno Upisana!",
            description=f"**Sveska:** {nb_title}\n**Naslov:** {title}\n\n```\n{tekst[:500]}\n```",
            color=0x34A853
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ Greška pri dodavanju beleške: {res.get('error')}")


@bot.tree.command(name="addurl", description="Dodaj veb stranicu ili YouTube video kao izvor u svesku")
@app_commands.describe(url="Veb URL ili YouTube link za indeksiranje")
async def addurl_slash(interaction: discord.Interaction, url: str):
    await interaction.response.defer(thinking=True)
    nb_id = get_channel_notebook(interaction.channel_id)
    nb_title = nlm.get_cached_title(nb_id)

    res = await nlm.add_source_url(nb_id, url)
    if res.get("success"):
        embed = discord.Embed(
            title="🌐 Novi Izvor je Poslat na Indeksiranje!",
            description=f"**Link:** `{url}`\n**Sveska:** {nb_title}",
            color=0x34A853
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"❌ Greška pri dodavanju linka: {res.get('error')}")


@bot.tree.command(name="newchat", description="Resetuj konverzacijski kontekst za novu temu")
async def newchat_slash(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    current_nb = get_channel_notebook(channel_id)
    title = nlm.get_cached_title(current_nb)

    if channel_id in channel_conversations:
        del channel_conversations[channel_id]
        await interaction.response.send_message(f"🔄 **Konverzacija je resetovana!** Sledeće pitanje počinje novu diskusiju u svesci **{title}**.")
    else:
        await interaction.response.send_message(f"✨ Konverzacija je već čista za svesku **{title}**.")


@bot.tree.command(name="current", description="Prikaži trenutno aktivnu svesku i sesiju")
async def current_slash(interaction: discord.Interaction):
    channel_id = interaction.channel_id
    current_nb = get_channel_notebook(channel_id)
    title = nlm.get_cached_title(current_nb)
    conv_id = channel_conversations.get(channel_id)

    embed = discord.Embed(
        title="🔍 Trenutno Stanje Sesije",
        color=0x34A853
    )
    embed.add_field(name="📖 Aktivna Sveska", value=f"**{title}**", inline=False)
    embed.add_field(name="🆔 Sveska ID", value=f"`{current_nb}`", inline=False)
    embed.add_field(name="💬 Konverzacijski ID", value=f"`{conv_id}`" if conv_id else "*Nema aktivne niti (započinje novu)*", inline=False)
    
    view = NotebookActionRow(current_nb)
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="status", description="Proveri stanje veze i zdravlje Google NotebookLM CLI-ja")
async def status_slash(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    auth_status = await nlm.check_auth()
    latency = round(bot.latency * 1000)

    embed = discord.Embed(
        title="🩺 Google NotebookLM Dijagnostika i Status",
        color=0x34A853 if auth_status.get("ok") else 0xEA4335
    )
    embed.add_field(name="CLI Verzija", value=f"`{auth_status.get('version', 'Nepoznato')}`", inline=True)
    embed.add_field(name="Google Auth", value="✅ Povezan i Autentifikovan" if auth_status.get("ok") else "❌ Nije povezan", inline=True)
    embed.add_field(name="Ukupno Svezaka", value=f"`{auth_status.get('notebook_count', 0)}`", inline=True)
    embed.add_field(name="Discord Latencija", value=f"`{latency}ms`", inline=True)
    embed.add_field(name="Aktivna Sveska Kanala", value=f"`{get_channel_notebook(interaction.channel_id)}`", inline=False)
    
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="help", description="Prikaži uputstvo i listu svih dostupnih komandi")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 Google NotebookLM Discord Asistent — Uputstvo",
        description="Direktno razgovaraj sa svojim Google NotebookLM bazama znanja bez simulacija ili mock-ova.",
        color=0x4285F4
    )
    embed.add_field(
        name="💬 Razgovor sa Sveskama",
        value=(
            "• `/ask <pitanje>` — Postavi pitanje aktivnoj svesci\n"
            "• `@Bot <pitanje>` — Taguj bota u bilo kom kanalu ili piši u DM\n"
            "• `/newchat` — Resetuj kontekst za novu temu"
        ),
        inline=False
    )
    embed.add_field(
        name="📚 Biranje i Pregled Svezaka",
        value=(
            "• `/notebooks` — Otvori padajući meni za izbor sveske\n"
            "• `/use <sveska>` — Pretraži i izaberi svesku uz automatsko dopunjavanje\n"
            "• `/sources` — Pregled svih fajlova i linkova u svesci\n"
            "• `/current` — Informacije o trenutnoj svesci"
        ),
        inline=False
    )
    embed.add_field(
        name="✍️ Dodavanje Podataka",
        value=(
            "• `/note` — Otvara pop-up prozor za pisanje nove beleške\n"
            "• `/addurl <url>` — Dodaje veb ili YouTube link u izvore sveske"
        ),
        inline=False
    )
    embed.add_field(
        name="⚙️ Dijagnostika i Sistem",
        value=(
            "• `/status` — Provera Google autentifikacije i latencije\n"
            "• `/sh <komanda>` — Bezbedno izvršavanje shell komande uz odobrenje"
        ),
        inline=False
    )
    embed.set_footer(text="Google NotebookLM Integration • 100% Real API")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="sh", description="Izvrši sistemsku shell komandu uz interaktivno odobrenje")
@app_commands.describe(komanda="Bash komanda za pokretanje na serveru")
async def sh_slash(interaction: discord.Interaction, komanda: str):
    view = ExecApprovalView(komanda, interaction.user.id)
    await interaction.response.send_message(
        f"🚨 **OpenClaw Čuvar** zahteva odobrenje za izvršavanje sistemske komande:\n`{komanda}`",
        view=view
    )


@bot.tree.command(
    name="execute",
    description="🤖 Pokreni autonomni kognitivni task kroz BrainCore + JudgeGuard pipeline"
)
@app_commands.describe(
    task="Opis zadatka koji agent treba da izvrši (npr. 'Analiziraj LinkedIn post strategiju')",
    sveska="Opciono: ID ili naziv sveske (podrazumevano: aktivna sveska kanala)"
)
@app_commands.autocomplete(sveska=notebook_autocomplete)
async def execute_slash(
    interaction: discord.Interaction,
    task: str,
    sveska: Optional[str] = None,
):
    """
    Antigravity 2.0 kognitivni šablon:
      Korak 1: RAG pretraga konteksta (hybrid: FTS5 + NotebookLM)
      Korak 2: VSR rezonovanje (Validate → Synthesize → Respond)
      Korak 3: JudgeGuard Quorum Verdict (HMAC + blacklist + freshness)
      Korak 4: Autonomna ekzekucija ili Halt Trigger
    """
    if not _BRAIN_AVAILABLE or brain is None or judge is None:
        await interaction.response.send_message(
            "❌ **BrainCore nije dostupan.** Proveri da li su `brain_core.py` i `judge_guard.py` "
            "prisutni i restartuj bota.",
            ephemeral=True
        )
        return

    await interaction.response.defer(thinking=True)

    nb_id = sveska or get_channel_notebook(interaction.channel_id)
    nb_title = nlm.get_cached_title(nb_id)
    user = interaction.user.name

    # ── KORAK 1: RAG context retrieval ──────────────────────────────────────
    status_embed = discord.Embed(
        title="🧠 Antigravity 2.0 — Kognitivni Pipeline",
        description=(
            f"**Task:** {task[:200]}\n"
            f"**Sveska:** {nb_title}\n\n"
            "```\n"
            "⟳ Korak 1/4: RAG pretraga konteksta (hybrid_rag)...\n"
            "```"
        ),
        color=0x4285F4
    )
    status_msg = await interaction.followup.send(embed=status_embed)

    try:
        knowledge_context = await brain.async_retrieve_context(
            task, strategy="hybrid_rag", notebook_id=nb_id
        )
    except Exception as exc:
        logger.exception("BrainCore retrieve_context greška")
        await status_msg.edit(
            embed=discord.Embed(
                title="❌ Greška u fazi 1 (RAG)",
                description=f"```{str(exc)[:400]}```",
                color=0xEA4335
            )
        )
        return

    # ── KORAK 2: VSR Reasoning ───────────────────────────────────────────────
    status_embed.description = (
        f"**Task:** {task[:200]}\n"
        f"**Sveska:** {nb_title}\n\n"
        "```\n"
        f"✅ Korak 1/4: Context retrieved ({len(knowledge_context.get('local_hits', []))} local + NLM)\n"
        "⟳ Korak 2/4: VSR rezonovanje...\n"
        "```"
    )
    await status_msg.edit(embed=status_embed)

    proposed_action = brain.reason(knowledge_context, task)
    confidence = proposed_action.get("confidence", 0.0)

    # ── KORAK 3: JudgeGuard Quorum Verdict ──────────────────────────────────
    status_embed.description = (
        f"**Task:** {task[:200]}\n"
        f"**Sveska:** {nb_title}\n\n"
        "```\n"
        f"✅ Korak 1/4: Context retrieved\n"
        f"✅ Korak 2/4: VSR done (confidence={confidence:.0%})\n"
        "⟳ Korak 3/4: JudgeGuard provera konsenzusa...\n"
        "```"
    )
    await status_msg.edit(embed=status_embed)

    judge.log_start(f"Discord /execute by {user}: {task[:60]}")
    verdict = judge.verify(proposed_action)

    # ── KORAK 4: Execute or Halt ─────────────────────────────────────────────
    if verdict == "PASSED":
        result = await brain.async_execute(proposed_action)
        judge.log_complete(f"Discord /execute: {task[:60]}")

        synthesis = result.get("output", "")
        sources_n = result.get("sources", proposed_action.get("sources_used", 0))

        final_embed = discord.Embed(
            title="✅ Task Izvršen — Antigravity 2.0",
            color=0x34A853
        )
        final_embed.add_field(name="📋 Task", value=task[:256], inline=False)
        final_embed.add_field(
            name="🔒 JudgeGuard",
            value=f"`PASSED` • Confidence: `{confidence:.0%}` • Sources: `{sources_n}`",
            inline=False
        )
        final_embed.add_field(name="📚 Sveska", value=nb_title, inline=True)
        final_embed.add_field(name="👤 Pokrenuo", value=user, inline=True)

        await status_msg.edit(embed=final_embed)

        # Send the actual synthesised answer
        if synthesis:
            chunks = split_text_for_discord(synthesis, max_chunk_size=1800)
            action_view = NotebookActionRow(nb_id)
            for idx, chunk in enumerate(chunks):
                if idx == len(chunks) - 1:
                    chunk += f"\n\n*📚 {nb_title} • 🔒 JudgeGuard PASSED*"
                if idx == 0:
                    if len(chunks) == 1:
                        await interaction.channel.send(chunk, view=action_view)
                    else:
                        await interaction.channel.send(chunk)
                elif idx == len(chunks) - 1:
                    await interaction.channel.send(chunk, view=action_view)
                else:
                    await interaction.channel.send(chunk)
    else:
        # HALT
        halt_result = brain.halt_system(reason=f"JudgeGuard BLOCKED for task: {task[:60]}")
        judge.log_blocked(task[:60], "Quorum verdict BLOCKED")

        halt_embed = discord.Embed(
            title="🛑 HALT — JudgeGuard je Blokirao Izvršavanje",
            description=(
                f"**Task:** {task[:200]}\n\n"
                f"**Razlog:** {halt_result.get('reason', 'Safety check failed')}\n\n"
                "Proveri `WORK_LOG.md` i ponovo pokreni ako je blokada zbog zastarelosti loga."
            ),
            color=0xEA4335
        )
        halt_embed.add_field(name="🔒 Verdict", value="`BLOCKED`", inline=True)
        halt_embed.add_field(name="📊 Confidence", value=f"`{confidence:.0%}`", inline=True)
        await status_msg.edit(embed=halt_embed)

# ── 10. PREFIX COMMANDS COMPATIBILITY (ZA `!` PREFIKS) ──

@bot.command(name="ask", aliases=["q", "nlm", "chat"])
async def ask_prefix(ctx, *, question: str):
    await execute_notebook_chat(ctx.message, question)

@bot.command(name="notebooks", aliases=["list", "nb"])
async def list_notebooks_prefix(ctx):
    global cached_notebook_list
    async with ctx.typing():
        cached_notebook_list = await nlm.list_notebooks(limit=50)

    if not cached_notebook_list:
        await ctx.send("❌ Nije pronađena nijedna sveska ili je došlo do greške.")
        return

    current_nb = get_channel_notebook(ctx.channel.id)
    view = NotebookSelectView(cached_notebook_list, current_nb)
    embed = view.build_embed()
    await ctx.send(embed=embed, view=view)

@bot.command(name="use", aliases=["select", "setnotebook"])
async def use_prefix(ctx, *, identifier: str):
    global cached_notebook_list
    identifier = identifier.strip()

    if not cached_notebook_list:
        cached_notebook_list = await nlm.list_notebooks(limit=50)

    selected_nb = None
    if identifier.isdigit():
        idx = int(identifier) - 1
        if 0 <= idx < len(cached_notebook_list):
            selected_nb = cached_notebook_list[idx]

    if not selected_nb and len(identifier) >= 8:
        for nb in cached_notebook_list:
            if identifier.lower() in nb.get("id", "").lower():
                selected_nb = nb
                break

    if not selected_nb:
        for nb in cached_notebook_list:
            if identifier.lower() in nb.get("title", "").lower():
                selected_nb = nb
                break

    if not selected_nb:
        await ctx.send(f"❌ Sveska sa parametrom `{identifier}` nije pronađena. Ukucaj `!notebooks` za listu.")
        return

    nb_id = selected_nb["id"]
    nb_title = selected_nb.get("title") or nb_id
    
    channel_notebooks[ctx.channel.id] = nb_id
    channel_conversations.pop(ctx.channel.id, None)

    embed = discord.Embed(
        title="✅ Aktivna Google NotebookLM Sveska je Promenjena!",
        color=0x34A853
    )
    embed.add_field(name="📖 Naslov", value=f"**{nb_title}**", inline=False)
    embed.add_field(name="🆔 Sveska ID", value=f"`{nb_id}`", inline=True)
    embed.add_field(name="📊 Broj Izvora", value=f"`{selected_nb.get('source_count', 0)}`", inline=True)
    view = NotebookActionRow(nb_id)
    await ctx.send(embed=embed, view=view)

@bot.command(name="sources", aliases=["docs", "files"])
async def list_sources_prefix(ctx, notebook_id: Optional[str] = None):
    nb_id = notebook_id or get_channel_notebook(ctx.channel.id)
    title = nlm.get_cached_title(nb_id)

    async with ctx.typing():
        sources = await nlm.list_sources(nb_id)

    if not sources:
        await ctx.send(f"📂 Sveska **{title}** nema dodatih izvora.")
        return

    embed = discord.Embed(
        title=f"📂 Izvori u svesci: {title}",
        description=f"Ukupno dokumenata/izvora: **{len(sources)}**",
        color=0xFBBC05
    )
    lines = [f"**{i}.** {s.get('title', 'Dokument')} `[{s.get('type', 'file')}]`" for i, s in enumerate(sources[:20], 1)]
    embed.description += "\n\n" + "\n".join(lines)
    if len(sources) > 20:
        embed.description += f"\n\n*...i još {len(sources) - 20} izvora.*"

    await ctx.send(embed=embed)

@bot.command(name="newchat", aliases=["reset", "clear"])
async def reset_chat_prefix(ctx):
    channel_id = ctx.channel.id
    current_nb = get_channel_notebook(channel_id)
    title = nlm.get_cached_title(current_nb)

    if channel_id in channel_conversations:
        del channel_conversations[channel_id]
        await ctx.send(f"🔄 **Konverzacija je resetovana!** Sledeće pitanje počinje novu diskusiju u svesci **{title}**.")
    else:
        await ctx.send(f"✨ Konverzacija je već čista za svesku **{title}**.")

@bot.command(name="note", aliases=["addnote"])
async def add_note_prefix(ctx, *, content: str):
    nb_id = get_channel_notebook(ctx.channel.id)
    title = nlm.get_cached_title(nb_id)

    async with ctx.typing():
        res = await nlm.add_note(nb_id, content=content, title=f"Note from Discord by {ctx.author.name}")

    if res.get("success"):
        await ctx.send(f"📝 **Nova beleška je uspešno upisana u Google NotebookLM!**\nSveska: **{title}**")
    else:
        await ctx.send(f"❌ Greška pri dodavanju beleške: {res.get('error')}")

@bot.command(name="addurl", aliases=["addsource"])
async def add_url_prefix(ctx, url: str):
    nb_id = get_channel_notebook(ctx.channel.id)
    title = nlm.get_cached_title(nb_id)

    async with ctx.typing():
        res = await nlm.add_source_url(nb_id, url)

    if res.get("success"):
        await ctx.send(f"🌐 **Link `{url}` je poslat u Google NotebookLM na indeksiranje!**\nSveska: **{title}**")
    else:
        await ctx.send(f"❌ Greška pri dodavanju linka: {res.get('error')}")

@bot.command(name="status", aliases=["health", "doctor"])
async def health_prefix(ctx):
    async with ctx.typing():
        auth_status = await nlm.check_auth()

    embed = discord.Embed(
        title="🩺 Google NotebookLM Dijagnostika i Status",
        color=0x34A853 if auth_status.get("ok") else 0xEA4335
    )
    embed.add_field(name="CLI Verzija", value=f"`{auth_status.get('version', 'Nepoznato')}`", inline=True)
    embed.add_field(name="Google Auth", value="✅ Povezan i Autentifikovan" if auth_status.get("ok") else "❌ Nije povezan", inline=True)
    embed.add_field(name="Ukupno Svezaka", value=f"`{auth_status.get('notebook_count', 0)}`", inline=True)
    embed.add_field(name="Aktivna Sveska Kanala", value=f"`{get_channel_notebook(ctx.channel.id)}`", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_prefix(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 **Pong!** Latencija bota: `{latency}ms` | Google NotebookLM CLI je aktivan.")

@bot.command(name="sh", aliases=["exec"])
async def sh_prefix(ctx, *, command: str):
    view = ExecApprovalView(command, ctx.author.id)
    await ctx.send(f"🚨 **OpenClaw Čuvar** zahteva odobrenje za izvršavanje sistemske komande:\n`{command}`", view=view)

@bot.command(name="help")
async def help_prefix(ctx):
    embed = discord.Embed(
        title="📖 Google NotebookLM Discord Asistent — Uputstvo",
        description="Direktno razgovaraj sa svojim Google NotebookLM bazama znanja bez simulacija ili mock-ova.",
        color=0x4285F4
    )
    embed.add_field(
        name="💬 Kako razgovarati sa sveskom?",
        value=(
            "• **Slash komanda:** `/ask <pitanje>`\n"
            "• **Taguj bota:** `@Bot Tvoje pitanje ovde`\n"
            "• **U DM-u:** Samo pošalji poruku\n"
            "• **Prefiks komanda:** `!ask <pitanje>`\n"
            "• Bot automatski pamti temu u niti dok ne ukucaš `/newchat`."
        ),
        inline=False
    )
    embed.add_field(
        name="📚 Upravljanje Sveskama",
        value=(
            "• `/notebooks` ili `!notebooks` — Izlistaj sveske sa padajućim menijem\n"
            "• `/use <sveska>` ili `!use <broj/naziv>` — Prebaci se na drugu svesku\n"
            "• `/sources` ili `!sources` — Pregled svih izvora i dokumenata\n"
            "• `/current` — Prikaz aktivne sveske i konverzacijske niti\n"
            "• `/newchat` — Resetuj kontekst"
        ),
        inline=False
    )
    embed.add_field(
        name="✍️ Dodavanje Sadržaja",
        value=(
            "• `/note` — Otvara pop-up prozor za unos nove beleške\n"
            "• `/addurl <link>` — Dodaj URL veb stranicu kao novi izvor"
        ),
        inline=False
    )
    embed.add_field(
        name="⚙️ Sistemske Komande",
        value=(
            "• `/status` — Provera veze, Google autentifikacije i latencije\n"
            "• `/ping` — Latencija bota\n"
            "• `/sh <komanda>` — Izvršavanje Linux shell komande (sa odobrenjem)"
        ),
        inline=False
    )
    embed.set_footer(text="Google NotebookLM Integration • 100% Real API")
    await ctx.send(embed=embed)

# ── 11. BACKGROUND HEARTBEAT ──
@tasks.loop(minutes=30)
async def heartbeat_task():
    logger.info("💓 HEARTBEAT aktiviran.")
    if os.path.exists(HEARTBEAT_FILE):
        try:
            with open(HEARTBEAT_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    logger.info(f"Heartbeat zadaci: {content[:100]}...")
        except Exception as e:
            logger.warning(f"Greška u heartbeat čitanju: {e}")

# ── 12. ENTRY POINT ──
if __name__ == "__main__":
    logger.info("Pokretanje Discord NotebookLM bota sa Slash Komandama...")
    bot.run(TOKEN)
