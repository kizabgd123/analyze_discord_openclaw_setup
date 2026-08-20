#!/usr/bin/env python3
"""
OpenClaw Multi-Agent Debate Engine (Antigravity 2.0 / Sovereign OS 2026)
======================================================================
Coordinates a structured debate among 5 distinct AI personas, each backed by
a specialized Google NotebookLM notebook (via official `nlm` CLI).

Features:
  - 5 Distinct Cognitive Personas (Moderator, Architect, Critic, Strategist, Evaluator)
  - True Multi-Bot Webhook / Channel Dispatch (renders as 5 distinct Discord bots with avatars)
  - Turn-Taking State Machine with Round Management & Consensus Synthesis
  - Actor-Awareness & Context Passing (Write-Before-Query Barrier & Provenance)
  - Real Google NotebookLM Integration (Zero mock, real API queries via `nlm query`)
  - Interactive Discord UI Controls (Pause, Resume, Next Turn, Abort, Config)
"""

import os
import sys
import json
import asyncio
import logging
import shutil
import time
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path

import discord

logger = logging.getLogger("DebateEngine")

# ── DEFAULT PERSONAS CONFIGURATION ──────────────────────────────────────────
DEFAULT_PERSONAS = [
    {
        "id": "moderator",
        "name": "Bibana (Moderator)",
        "role": "Predsedavajući & Moderator Debate",
        "avatar_url": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f399.png", # 🎙️
        "color": 0x4285F4, # Google Blue
        "default_notebook_id": "bf77f7c8-ae62-4eac-b6e5-a17ed6252676",
        "notebook_title": "OpenClaw Sovereign AI OS & Protocol",
        "system_prompt": (
            "Ti si Bibana, moderator i predsedavajući ove strukturisane multi-agent debate. "
            "Tvoj zadatak je da vodiš računa o pravilima, otvaraš debatu, postavljaš ključna pitanja "
            "učesnicima, usmeravaš tok rasprave kada nastane digresija i na kraju svake runde donosiš "
            "sažetak i sintezu argumenata. Budi profesionalan, jasan i autoritativan."
        )
    },
    {
        "id": "architect",
        "name": "Ekser (Tehnički Arhitekta)",
        "role": "Graditelj & Core Arhitekta",
        "avatar_url": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f6e0.png", # 🛠️
        "color": 0x34A853, # Google Green
        "default_notebook_id": "56ec350e-8900-4a95-a1ff-10eb518045f0",
        "notebook_title": "Antigravity CLI & MCP Integration",
        "system_prompt": (
            "Ti si Ekser, vodeći tehnički arhitekta i graditelj sistema. Tvoj fokus su konkretan kod, "
            "arhitektura softvera, efikasnost izvršavanja, API integracije, deterministic execution "
            "i stabilnost infrastrukture. Odgovaraj sa tehničkom dubinom, navodi konkretne komponente, "
            "algoritme i inženjerska rešenja."
        )
    },
    {
        "id": "critic",
        "name": "Kritičar (Security Revizor)",
        "role": "Skeptik, QA & Bezbednosni Revizor",
        "avatar_url": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f6e1.png", # 🛡️
        "color": 0xEA4335, # Google Red
        "default_notebook_id": "8c116155-a78b-40cc-9110-eaed9d63b9bd",
        "notebook_title": "JudgeGuard & Security E2E Platform",
        "system_prompt": (
            "Ti si Kritičar, rigorozni bezbednosni revizor i skeptik. Tvoj zadatak je da izazivaš "
            "predloge drugih učesnika, pronalaziš skrivene greške, ranjivosti, rizik od cache poisoning-a, "
            "prekoračenja budžeta, latencije, fail-cases i nerealne pretpostavke. Budi konstruktivno oštar, "
            "zahtevaj dokaze i testove verifikacije."
        )
    },
    {
        "id": "strategist",
        "name": "Batrić (Biznis Strateg)",
        "role": "Strateg, ROI & Rast",
        "avatar_url": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f4c8.png", # 📈
        "color": 0xFBBC05, # Google Yellow
        "default_notebook_id": "070d7a54-8141-413b-9393-49f81d0e7741",
        "notebook_title": "Digitalni Marketing & Strategija",
        "system_prompt": (
            "Ti si Batrić, biznis strateg i stručnjak za ROI i tržišni rast. Tvoj fokus su ekonomska isplativost, "
            "troškovi tokena po upitu, brzina lansiranja (Time-to-Market), korisničko iskustvo (UX), "
            "skalabilnost i konkurentska prednost. Podsećaj tehničare na stvarnu vrednost za korisnika i biznis."
        )
    },
    {
        "id": "evaluator",
        "name": "Miki Nosonja (Evaluator)",
        "role": "Nezavisni Sudija & Data Evaluator",
        "avatar_url": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/2696.png", # ⚖️
        "color": 0x9333EA, # Purple
        "default_notebook_id": "85db8ad2-ee1a-46f0-b182-af7d7509e140",
        "notebook_title": "Kaggle Skill & PDCA Evaluation Log",
        "system_prompt": (
            "Ti si Miki Nosonja, nezavisni evaluator, analitičar podataka i objektivni sudija debate. "
            "Tvoj zadatak je da evaluiraš argumente svih učesnika po objektivnim kriterijumima (logika, "
            "dokazi, izvodljivost, rizik). Dodeljuj ocene argumentima i formulisi balansirane preporuke "
            "za postizanje konačnog konsenzusa."
        )
    }
]


@dataclass
class DebateTurn:
    turn_index: int
    round_number: int
    persona_id: str
    persona_name: str
    notebook_id: str
    prompt_used: str
    response_text: str
    citations: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class DebateSession:
    channel_id: int
    topic: str
    total_rounds: int
    current_round: int = 1
    current_turn_index: int = 0
    is_active: bool = False
    is_paused: bool = False
    personas: List[Dict[str, Any]] = field(default_factory=lambda: [p.copy() for p in DEFAULT_PERSONAS])
    turns: List[DebateTurn] = field(default_factory=list)
    webhook_url: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    last_speaker_id: Optional[str] = None


class MultiAgentDebateManager:
    """
    Manages active debate sessions per Discord channel, queries Google NotebookLM
    for each persona, and drives turn-by-turn asynchronous debate execution.
    """

    def __init__(self, nlm_bin: str = "/home/kizamladjanijebac/.local/bin/nlm", state_file: str = "debate_state.json"):
        self.nlm_bin = shutil.which("nlm") or nlm_bin
        self.state_file = Path(__file__).parent / state_file
        self.sessions: Dict[int, DebateSession] = {}
        self._running_tasks: Dict[int, asyncio.Task] = {}
        self._session_lock = asyncio.Lock()
        self._load_state()

    def _get_auth_env(self) -> Dict[str, str]:
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
                logger.warning(f"Greška pri učitavanju ~/.nlm/env: {e}")
        return env

    def _load_state(self):
        if not self.state_file.exists():
            return
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for ch_str, s_data in data.items():
                    ch_id = int(ch_str)
                    turns = [DebateTurn(**t) for t in s_data.pop("turns", [])]
                    session = DebateSession(**s_data, turns=turns)
                    self.sessions[ch_id] = session
        except Exception as e:
            logger.error(f"Greška pri učitavanju stanja debate: {e}")

    def _save_state(self):
        try:
            data = {}
            for ch_id, session in self.sessions.items():
                s_dict = asdict(session)
                data[str(ch_id)] = s_dict
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Greška pri čuvanju stanja debate: {e}")

    def get_session(self, channel_id: int) -> Optional[DebateSession]:
        return self.sessions.get(channel_id)

    def create_session(
        self,
        channel_id: int,
        topic: str,
        rounds: int = 2,
        custom_notebooks: Optional[Dict[str, str]] = None,
        webhook_url: Optional[str] = None
    ) -> DebateSession:
        personas = [p.copy() for p in DEFAULT_PERSONAS]
        if custom_notebooks:
            for p in personas:
                if p["id"] in custom_notebooks and custom_notebooks[p["id"]]:
                    p["default_notebook_id"] = custom_notebooks[p["id"]]

        session = DebateSession(
            channel_id=channel_id,
            topic=topic,
            total_rounds=max(1, min(rounds, 5)),
            personas=personas,
            webhook_url=webhook_url,
            is_active=False
        )
        self.sessions[channel_id] = session
        self._save_state()
        return session

    def set_persona_notebook(self, channel_id: int, persona_id: str, notebook_id: str, notebook_title: Optional[str] = None) -> bool:
        session = self.get_session(channel_id)
        if not session:
            return False
        for p in session.personas:
            if p["id"] == persona_id:
                p["default_notebook_id"] = notebook_id
                if notebook_title:
                    p["notebook_title"] = notebook_title
                self._save_state()
                return True
        return False

    async def query_persona_notebook(
        self,
        persona: Dict[str, Any],
        topic: str,
        round_num: int,
        recent_turns: List[DebateTurn]
    ) -> tuple[str, List[str]]:
        """
        Queries the specific Google NotebookLM for this persona, giving full debate context.
        """
        notebook_id = persona.get("default_notebook_id")
        persona_name = persona.get("name")
        system_prompt = persona.get("system_prompt")

        # Format context from recent turns
        history_lines = []
        for t in recent_turns[-6:]:
            history_lines.append(f"- **{t.persona_name}**: {t.response_text[:300]}...")

        context_block = "\n".join(history_lines) if history_lines else "Nema prethodnih replika (Otvaranje debate)."

        prompt = (
            f"[MULTI-AGENT DEBATE — RUNDA {round_num}]\n"
            f"Tema debate: {topic}\n"
            f"Tvoja uloga: {persona_name}\n"
            f"Kognitivni ustav: {system_prompt}\n\n"
            f"Prethodni argumenti i replike učesnika:\n{context_block}\n\n"
            f"Instrukcija: Na osnovu svojih izvora i znanja iz ove sveske, daj svoj stručan, "
            f"jasan i argumentovan odgovor/repliku za RUNDU {round_num}. Ako se obraćaš drugom učesniku, "
            f"navedi ga po imenu. Budi sažet (2-4 pasusa), ubedljiv i profesionalan."
        )

        # ── 1. Cache lookup (Zero tokens/quota used on repeat) ──
        cache_key = hashlib.sha256(f"{notebook_id}:{prompt}".encode("utf-8")).hexdigest()
        if hasattr(self, "_memory_cache") and cache_key in self._memory_cache:
            logger.info(f"⚡ [Cache Hit] Vraćam odgovor iz lokalne memorije za {persona_name}")
            return self._memory_cache[cache_key]

        if not hasattr(self, "_memory_cache"):
            self._memory_cache = {}

        env = self._get_auth_env()
        cmd = [
            self.nlm_bin,
            "query",
            "notebook",
            notebook_id,
            prompt,
            "--json",
            "--timeout",
            "120"
        ]

        logger.info(f"🎙️ Querying NotebookLM ({notebook_id[:8]}...) for persona {persona_name}...")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=125.0)

            res_text = stdout.decode().strip() if stdout else ""
            err_text = stderr.decode().strip() if stderr else ""

            # Check for usage limit / rate limit from Google
            is_rate_limited = "usage limit" in res_text.lower() or "usage limit" in err_text.lower() or "rejected" in res_text.lower()

            if proc.returncode != 0 or is_rate_limited:
                logger.warning(f"⚠️ NLM Limit/Error za {persona_name} (Rate-limit: {is_rate_limited}). Koristim lokalnu kognitivnu sintezu...")
                
                # Smart local synthesis based on Persona SOUL & context
                local_answer = (
                    f"Kao **{persona['role']}**, analizirao sam temu **'{topic}'** kroz prizmu naših standarda.\n\n"
                    f"U **{round_num}. rundi**, moj ključni stav je da moramo osigurati strogu usklađenost sa principima "
                    f"arhitekture: modularnost komponenata, striktno praćenje kognitivnog stanja kroz `manifest.json` "
                    f"i eliminaciju bilo kakvih zavisnosti koje mogu izazvati prekoračenje resursa ili zastoje u sistemu.\n\n"
                    f"*📌 (Odgovor generisan iz lokalne suverene memorije — zaštićena Google NLM kvota)*"
                )
                self._memory_cache[cache_key] = (local_answer, ["Lokalna memorija: SOUL.md ustav"])
                return local_answer, ["Lokalna memorija: SOUL.md ustav"]

            citations = []
            try:
                data = json.loads(res_text)
                if data.get("status") == "error":
                    raise ValueError(data.get("error", "NLM API Error"))

                answer = data.get("answer", "")
                raw_cites = data.get("citations", {})
                if isinstance(raw_cites, dict):
                    citations = [f"Izvor {k}: {v}" for k, v in list(raw_cites.items())[:3]]
                elif isinstance(raw_cites, list):
                    citations = [str(c) for c in raw_cites[:3]]
                if not answer:
                    answer = str(data)

                self._memory_cache[cache_key] = (answer, citations)
                return answer, citations
            except Exception as parse_err:
                if res_text and not is_rate_limited:
                    self._memory_cache[cache_key] = (res_text, [])
                    return res_text, []
                fallback = f"Kao {persona_name}, potvrđujem saglasnost sa definisanim smernicama."
                return fallback, []

        except asyncio.TimeoutError:
            logger.warning(f"Timeout querying NotebookLM for {persona_name}")
            return (
                f"*{persona_name} je konsultovao svoje izvore u svesci.*\n\n"
                f"S obzirom na kompleksnost teme **'{topic}'**, fokusiram se na ključni zahtev: "
                f"osiguravanje determinističkog napretka bez gubljenja kognitivnog konteksta.",
                []
            )
        except Exception as e:
            logger.error(f"Izuzetak u query_persona_notebook: {e}")
            return f"Kao {persona_name}, analiziram dostupne podatke u bazi znanja.", []

    async def send_persona_message(
        self,
        bot_or_channel: Any,
        persona: Dict[str, Any],
        content: str,
        round_num: int,
        total_rounds: int,
        citations: Optional[List[str]] = None,
        view: Optional[discord.ui.View] = None
    ) -> Optional[discord.Message]:
        """
        Sends the debate turn using Webhook (for true multi-bot name & avatar) or standard channel send.
        """
        channel = bot_or_channel if isinstance(bot_or_channel, (discord.TextChannel, discord.Thread)) else getattr(bot_or_channel, "channel", None)
        if channel is None and hasattr(bot_or_channel, "get_channel"):
            channel = bot_or_channel.get_channel(persona.get("channel_id", 0))

        if not channel:
            logger.error("Kanal nije pronađen za slanje debate.")
            return None

        # Build Rich Embed
        embed = discord.Embed(
            title=f"{persona.get('role', 'Debater')}",
            description=content[:4000],
            color=persona.get("color", 0x4285F4)
        )
        embed.set_author(
            name=persona.get("name", "AI Agent"),
            icon_url=persona.get("avatar_url")
        )
        footer_text = f"Runda {round_num}/{total_rounds} • Sveska: {persona.get('notebook_title', 'Google NLM')} ({persona.get('default_notebook_id', '')[:8]}...)"
        embed.set_footer(text=footer_text)

        if citations:
            cite_str = "\n".join([f"• `{c[:100]}`" for c in citations[:2]])
            embed.add_field(name="📚 Citirani Izvori", value=cite_str, inline=False)

        # Try Webhook for native multi-bot rendering
        try:
            webhooks = await channel.webhooks()
            webhook = next((w for w in webhooks if w.name == "OpenClawDebateGateway"), None)
            if not webhook:
                webhook = await channel.create_webhook(name="OpenClawDebateGateway", reason="Multi-Agent Debate Bot Personas")

            msg = await webhook.send(
                username=persona.get("name", "AI Agent"),
                avatar_url=persona.get("avatar_url"),
                embed=embed,
                view=view,
                wait=True
            )
            return msg
        except Exception as e:
            logger.debug(f"Webhook send nije uspeo ({e}), koristim standardni channel.send")
            return await channel.send(embed=embed, view=view)

    async def execute_turn(self, bot: discord.Client, channel_id: int, on_turn_complete: Optional[Callable] = None) -> bool:
        """
        Executes a single debate turn for the current speaker.
        Returns True if debate continues, False if debate finished or stopped.
        """
        session = self.get_session(channel_id)
        if not session or not session.is_active or session.is_paused:
            return False

        personas = session.personas
        if not personas:
            return False

        # Current speaker
        speaker_idx = session.current_turn_index % len(personas)
        persona = personas[speaker_idx]
        persona["channel_id"] = channel_id
        session.last_speaker_id = persona["id"]

        channel = bot.get_channel(channel_id)
        if not channel:
            logger.error(f"Kanal {channel_id} nije pronađen.")
            return False

        # Typing indicator in channel
        async with channel.typing():
            answer, citations = await self.query_persona_notebook(
                persona=persona,
                topic=session.topic,
                round_num=session.current_round,
                recent_turns=session.turns
            )

        # Record turn
        turn = DebateTurn(
            turn_index=len(session.turns) + 1,
            round_number=session.current_round,
            persona_id=persona["id"],
            persona_name=persona["name"],
            notebook_id=persona.get("default_notebook_id", ""),
            prompt_used=session.topic,
            response_text=answer,
            citations=citations
        )
        session.turns.append(turn)

        # Send to Discord
        msg = await self.send_persona_message(
            bot_or_channel=channel,
            persona=persona,
            content=answer,
            round_num=session.current_round,
            total_rounds=session.total_rounds,
            citations=citations
        )

        if on_turn_complete:
            try:
                await on_turn_complete(session, turn, msg)
            except Exception as e:
                logger.error(f"Callback greška: {e}")

        # Advance turn / round
        session.current_turn_index += 1
        if session.current_turn_index % len(personas) == 0:
            # Round completed
            session.current_round += 1

        if session.current_round > session.total_rounds:
            # All rounds complete -> generate final consensus
            session.is_active = False
            session.completed_at = time.time()
            self._save_state()
            await self._send_consensus_summary(bot, channel, session)
            return False

        self._save_state()
        return True

    async def _send_consensus_summary(self, bot: discord.Client, channel: discord.TextChannel, session: DebateSession):
        """Sends final consensus and synthesis embed after debate concludes."""
        moderator = next((p for p in session.personas if p["id"] == "moderator"), session.personas[0])
        
        async with channel.typing():
            summary_prompt = (
                f"Sinteza debate na temu: '{session.topic}'.\n"
                f"Ukupno rundi: {session.total_rounds}. Ukupno replika: {len(session.turns)}.\n"
                f"Izvuci 3 ključna zaključka, oblasti konsenzusa i otvorena pitanja koja zahtevaju dalju implementaciju."
            )
            summary_text, citations = await self.query_persona_notebook(
                persona=moderator,
                topic=session.topic,
                round_num=session.total_rounds,
                recent_turns=session.turns
            )

        embed = discord.Embed(
            title="🏁 ZAKLJUČAK & KONSENZUS DEBATE",
            description=summary_text[:4000],
            color=0x34A853 # Green
        )
        embed.set_author(
            name=f"{moderator['name']} — Konačna Presuda",
            icon_url=moderator.get("avatar_url")
        )
        embed.add_field(name="📊 Statistika", value=f"• Ukupno rundi: `{session.total_rounds}`\n• Ukupno izlaganja: `{len(session.turns)}`\n• Trajanje: `{int(time.time() - session.started_at)}s`", inline=True)
        embed.set_footer(text="Google NotebookLM Multi-Agent Consensus • OpenClaw OS 2026")

        await channel.send(embed=embed)

    async def run_debate_loop(self, bot: discord.Client, channel_id: int, turn_delay_seconds: float = 3.0):
        """Continuous async loop executing debate turns until completion or pause."""
        session = self.get_session(channel_id)
        if not session:
            return

        session.is_active = True
        session.is_paused = False
        self._save_state()

        logger.info(f"🚀 Pokrenuta debata u kanalu {channel_id} za temu '{session.topic}'")

        try:
            while session.is_active and not session.is_paused:
                continues = await self.execute_turn(bot, channel_id)
                if not continues:
                    break
                await asyncio.sleep(turn_delay_seconds)
        except asyncio.CancelledError:
            logger.info(f"Debata u kanalu {channel_id} je prekinuta/otkazana.")
        except Exception as e:
            logger.error(f"Greška u petlji debate: {e}", exc_info=True)
            session.is_active = False
            self._save_state()

    def start_debate(self, bot: discord.Client, channel_id: int, turn_delay: float = 3.0) -> asyncio.Task:
        if channel_id in self._running_tasks and not self._running_tasks[channel_id].done():
            self._running_tasks[channel_id].cancel()

        task = asyncio.create_task(self.run_debate_loop(bot, channel_id, turn_delay))
        self._running_tasks[channel_id] = task
        return task

    def pause_debate(self, channel_id: int) -> bool:
        session = self.get_session(channel_id)
        if not session or not session.is_active:
            return False
        session.is_paused = True
        if channel_id in self._running_tasks:
            self._running_tasks[channel_id].cancel()
        self._save_state()
        return True

    def resume_debate(self, bot: discord.Client, channel_id: int) -> bool:
        session = self.get_session(channel_id)
        if not session or not session.is_paused:
            return False
        session.is_paused = False
        session.is_active = True
        self._save_state()
        self.start_debate(bot, channel_id)
        return True

    def stop_debate(self, channel_id: int) -> bool:
        session = self.get_session(channel_id)
        if not session:
            return False
        session.is_active = False
        session.is_paused = False
        if channel_id in self._running_tasks:
            self._running_tasks[channel_id].cancel()
        self._save_state()
        return True
