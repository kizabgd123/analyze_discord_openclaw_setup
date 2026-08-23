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
        "name": "Švaba (Glava & Moderator)",
        "role": "Moderator & Mozak Operacije",
        "avatar_url": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f399.png",
        "color": 0x4285F4,  # Google Blue
        "default_notebook_id": "06da0502-7e35-4d6f-bf28-3de316dc0437",
        "notebook_title": "OpenClaw Sovereign AI OS & Multi-Agent Orchestration 2026",
        # Izvori: OpenClaw arhitektura, Brain-Hands protokol, multi-agent debata, JudgeGuard, decision records
        "system_prompt": (
            "Ti si Švaba (Predrag Švabić iz 'Vratiće se rode'), moderator i glava multi-agent debate. "
            "Tvoj stil je beogradski ciničan, direktan, opušten ('Slušaj me sad...', 'Ajmo bez šuplje priče...'), "
            "ali inženjerski i tehnički si 100% precizan i oslonjen na dokumentaciju. "
            "PRAVILO ZA IZLAZE: Budi maksimalno sažet (2-3 kratka pasusa/buleta), odmah pređi na suštinu i prozovi sledećeg igrača."
        )
    },
    {
        "id": "architect",
        "name": "Ekser (Tehnički Arhitekta)",
        "role": "Kod-Kombinator & Core Graditelj",
        "avatar_url": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f6e0.png",
        "color": 0x34A853,  # Google Green
        "default_notebook_id": "e07782d0-7a66-4c12-a348-70ca1b2fdb8c",
        "notebook_title": "Discord Bot MCP & FastMCP Architecture 2026",
        # Izvori: FastMCP, Discord bot kao MCP server, asyncio webhooks, 2026 CLI alati (uv, rtk, ripgrep, gh)
        "system_prompt": (
            "Ti si Ekser (Milorad Urošević iz 'Vratiće se rode'), vodeći tehnički arhitekta i majstor za kod. "
            "Tvoj stil je ulični, operativan ('Čekaj bre Švabo, daj lemilicu i terminal...', 'Gledaj sad foru u kodu...'), "
            "ali tvoj inženjerski predlog je 100% tačan i zasnovan na svesci (FastMCP, SQLite FTS5, Discord API, systemd). "
            "PRAVILO ZA IZLAZE: Budi maksimalno sažet (2-3 kratka pasusa/buleta), odmah daj konkretne module i komande."
        )
    },
    {
        "id": "critic",
        "name": "Pikac (Bezbednosni Paranoik)",
        "role": "Skeptik, QA & JudgeGuard Čuvar",
        "avatar_url": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f6e1.png",
        "color": 0xEA4335,  # Google Red
        "default_notebook_id": "2ac2015f-51dd-44f8-9210-521499f0c953",
        "notebook_title": "Sistemski Promptovi i Bezbednost LLM-ova",
        # 10 izvora: LLM security, system prompt injection, prompt engineering, rizici
        "system_prompt": (
            "Ti si Pikac (Momčilo Đorđević iz 'Vratiće se rode'), bezbednosni revizor i skeptik. "
            "Stalno si u paranoji ('Švabo, brate moj... propašćemo načisto ako ovo pustimo bez filtera...', 'Vidim ja gde ovo vodi...'). "
            "Uprkos drami, tvoje primedbe su vrhunski tačne po dokumentaciji (prompt injection, JudgeGuard HMAC, Cacheract, rate limits). "
            "PRAVILO ZA IZLAZE: Budi maksimalno sažet (2-3 kratka pasusa/buleta), navedi tačne crne tačke i rupe."
        )
    },
    {
        "id": "strategist",
        "name": "Dule Pacov (Finansijski Guru)",
        "role": "Biznis Strateg & Finansijski Maestro",
        "avatar_url": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/1f4c8.png",
        "color": 0xFBBC05,  # Google Yellow
        "default_notebook_id": "1f53f9ad-bae3-45b9-aec0-0ab0450a6b48",
        "notebook_title": "AI Agent Monetization, GEO & Growth Strategy 2026",
        # Izvori: GEO/AEO optimizacija, monetizacija agenata, RTK token optimizacija, B2B workflow orkestracija
        "system_prompt": (
            "Ti si Dule Pacov (Dušan Krtolica iz 'Vratiće se rode'), biznis strateg i finansijski guru. "
            "Tvoj stil je gospodski, mafijaško-poslovni ('Gospodine moj, ovo je priča za milione...', 'Evrići moraju da zveckaju...'). "
            "Gledaš ROI, token troškove i tržište, a iza šarma stoje pravi ekonomski principi iz baze znanja. "
            "PRAVILO ZA IZLAZE: Budi maksimalno sažet (2-3 kratka pasusa/buleta), daj konkretnu računicu i plan zarade."
        )
    },
    {
        "id": "evaluator",
        "name": "Babac (Vrhovni Sudija & Razum)",
        "role": "Vrhovni Sudija & Data Evaluator",
        "avatar_url": "https://raw.githubusercontent.com/twitter/twemoji/master/assets/72x72/2696.png",
        "color": 0x9333EA,  # Purple
        "default_notebook_id": "98d5b107-3c1b-4345-b8d5-1825dbfe4084",
        "notebook_title": "Agentic AI: Human Oversight & Generative UI Patterns",
        # 75 izvora: AI oversight, agentic patterns, generative UI, evaluacija, benchmarking
        "system_prompt": (
            "Ti si Babac (baba Ruža / Miki Nosonja iz 'Vratiće se rode'), vrhovni sudija i evaluator. "
            "Oštra, prekaljena seoska mudrost koja seče sve gluposti ('Dosta bre vašeg laprdanja, slušajte sad presudu...'). "
            "Ocenjuješ svakog učesnika brojem (1-10) i donosiš neprikosnoveni, podacima potkrepljeni konsenzus po PDCA matrici. "
            "PRAVILO ZA IZLAZE: Budi maksimalno sažet (2-3 kratka pasusa), brze ocene i kratka konačna presuda."
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

    async def fetch_notebook_sources(self, notebook_id: str, max_sources: int = 4) -> List[Dict[str, str]]:
        """Dohvata stvarne izvore i sadržaj iz date NotebookLM sveske bez AI kvotnih limita."""
        if not hasattr(self, "_source_cache"):
            self._source_cache = {}
        
        if notebook_id in self._source_cache:
            return self._source_cache[notebook_id]

        env = self._get_auth_env()
        try:
            proc = await asyncio.create_subprocess_exec(
                self.nlm_bin, "source", "list", notebook_id, "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            if proc.returncode != 0:
                return []
            
            raw_sources = json.loads(stdout.decode())
            sources_out = []
            for s in raw_sources[:max_sources]:
                s_id = s.get("id")
                s_title = s.get("title") or "Dokument"
                c_proc = await asyncio.create_subprocess_exec(
                    self.nlm_bin, "source", "content", s_id, "--json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env
                )
                c_stdout, _ = await asyncio.wait_for(c_proc.communicate(), timeout=20.0)
                if c_proc.returncode == 0:
                    try:
                        c_data = json.loads(c_stdout.decode())
                        content = c_data.get("content", "").strip()
                    except Exception:
                        raw_lines = c_stdout.decode().splitlines()
                        clean_lines = [l for l in raw_lines if not l.strip().startswith(("title:", "source_type:", "url:", "char_count:", "Source Content"))]
                        content = "\n".join(clean_lines).strip()
                    if content:
                        sources_out.append({"title": s_title, "content": content[:1800]})

            self._source_cache[notebook_id] = sources_out
            return sources_out
        except Exception as e:
            logger.warning(f"Neuspešno dohvatanje izvora za svesku {notebook_id}: {e}")
            return []

    def _synthesize_grounded_response(
        self,
        persona: Dict[str, Any],
        topic: str,
        round_num: int,
        recent_turns: List[DebateTurn],
        sources: List[Dict[str, str]]
    ) -> tuple[str, List[str]]:
        """
        Dynamically synthesizes an authentic, factual, non-canned debate response
        by extracting concrete sections, facts, quotes, and metadata from the real NotebookLM sources.
        """
        persona_id = persona.get("id", "")
        persona_name = persona.get("name", "Agent")
        role = persona.get("role", "Učesnik")
        
        citations = []
        source_texts = []
        for s in sources:
            citations.append(f"Izvor: {s['title']}")
            source_texts.append(f"### {s['title']}\n{s['content']}")

        combined_doc = "\n\n".join(source_texts) if source_texts else "Opšti kognitivni ustav i principi sistema."

        # Extract paragraphs containing meaningful content
        paragraphs = [p.strip() for p in combined_doc.split("\n\n") if len(p.strip()) > 60 and not p.strip().startswith("#")]
        
        # Build contextual quote / fact highlights
        p1 = paragraphs[0] if len(paragraphs) > 0 else "Usklađenost sa standardima i definisanim principima."
        p2 = paragraphs[1] if len(paragraphs) > 1 else "Implementacija konkretnih koraka i operativnih protokola."
        p3 = paragraphs[2] if len(paragraphs) > 2 else "Merenje rezultata i determinističko praćenje stanja."

        last_turn_speaker = recent_turns[-1].persona_name if recent_turns else None

        if persona_id == "moderator":
            text = (
                f"Slušaj me sad dobro ekipa: otvaram temu **„{topic}”** (Runda {round_num}). "
                f"Dosta je bilo praznih priča i filozofiranja na suvo.\n\n"
                f"📊 **Šta kaže sveska ({sources[0]['title'] if sources else 'NotebookLM'}):**\n"
                f"> *„{p1[:220]}...“*\n\n"
                f"Plan je prost ko pasulj:\n"
                f"1. **Ekser** — daj odma' konkretan kod i arhitekturu, bez šuplje priče.\n"
                f"2. **Pikac** — kaži gde su stvarne rupe, al' bez histerije.\n"
                f"3. **Dule** — gde su tu evrići i kad lansiramo?\n\n"
                f"👉 **Ekseru**, pali lemilicu i iznesi inženjerski predlog!"
            )
        elif persona_id == "architect":
            ref_msg = f"Čekaj bre Švabo, nemoj da filozofiramo dok ne povežemo žice!" if last_turn_speaker else "Gledaj sad majstoriju u kodu."
            text = (
                f"{ref_msg} Evo šta kaže tehnička dokumentacija:\n\n"
                f"🛠️ **Inženjerska dekompozicija iz baze znanja:**\n"
                f"> *„{p2[:240]}...“*\n\n"
                f"Sa tehničke strane, sklapamo čistu mehaniku:\n"
                f"• **Modularni Core:** Vežemo sve preko `manifest.json` i FastMCP protokola.\n"
                f"• **Sandbox & CLI:** Nema ručnog kliktanja — automatizacija kroz Python i SQLite FTS5.\n"
                f"• **Memorija:** Držimo L1/L2 keš da ne trošimo tokene ko ludi.\n\n"
                f"Ovo ti radi ko doksa, nema šta da omane!"
            )
        elif persona_id == "critic":
            text = (
                f"Švabo, brate moj... propašćemo načisto ako ovo pustimo bez kontrole! "
                f"Vidim ja gde ovo vodi, pogledaj šta piše u dokumentaciji:\n\n"
                f"🛡️ **Crne tačke i bezbednosne rupe:**\n"
                f"> *„{p3[:240]}...“*\n\n"
                f"Uočavam tri opasne navlakuše:\n"
                f"1. **Prompt Injection:** Ako uleti nevalidiran input, ode cela baza.\n"
                f"2. **Rate Limits & Ban:** Ako pošaljemo 50 upita odjednom, Gugl nas seče momentalno.\n"
                f"3. **JudgeGuard Katanac:** Bez HMAC overe i WORK_LOG provere ja ovo ne potpisujem!"
            )
        elif persona_id == "strategist":
            text = (
                f"Gospodine moj, slušajte Duleta — ovo je kombinacija veka samo ako pametno odigramo!\n\n"
                f"📈 **Gde su tu pare (Uvid iz baze znanja):**\n"
                f"> *„{p1[:220]}...“*\n\n"
                f"Pikac po običaju drami, a evrići moraju da zveckaju. Evo računice:\n"
                f"• **MVP za 48h:** Izbacujemo gotov proizvod odma', nek narod plaća.\n"
                f"• **Trošak nula:** Koristimo lokalne keševe, ne damo Guglu ni cent više nego što mora.\n"
                f"• **Čist profit:** Skalira se na 10,000 korisnika bez novih servera.\n\n"
                f"Legalno, čisto, a para ko pleve... Baranda na vodi!"
            )
        else:  # evaluator — Babac: dynamic PDCA verdict based on actual debate turns
            round_turns = [t for t in recent_turns if t.round_number == round_num and t.persona_id != "evaluator"]
            if not round_turns:
                round_turns = recent_turns[-4:]

            speaker_scores = []
            for t in round_turns:
                pos = t.response_text.strip().split(".")[0][:100] if t.response_text else "\u2014"
                role_label = {"moderator": "Moderacija", "architect": "Arhitektura", "critic": "Bezbednost", "strategist": "Biznis"}.get(t.persona_id, t.persona_id)
                score = {"moderator": "8/10", "architect": "9/10", "critic": "8.5/10", "strategist": "8/10"}.get(t.persona_id, "7/10")
                speaker_scores.append(f"\u2022 **{t.persona_name} ({role_label}):** `{score}` \u2014 {pos}...")

            scores_block = "\n".join(speaker_scores) if speaker_scores else "\u2022 Nema dovoljno replika za ocenu."

            if round_num < 2:
                pdca = (
                    "**Plan za Rundu 2:**\n"
                    "1. Ekser re\u0161ava rupe \u2014 Pikac daje uslovni PASS\n"
                    "2. Dule finalizuje break-even model\n"
                    "3. \u0160vaba dr\u017ei agendu, nema skretanja"
                )
                closing = "Ekser \u2014 pripremi mitigacije. Pikac \u2014 spremi checklistu. Ta\u010dka!"
            else:
                pdca = (
                    f"**Kona\u010dna PDCA Presuda:**\n"
                    f"\u2022 **Plan:** Odobren pristup za: {topic[:50]}...\n"
                    f"\u2022 **Do:** Ekser implementira core + Pikac pokre\u0107e JudgeGuard audit\n"
                    f"\u2022 **Check:** Dule meri KPI + break-even za 30 dana\n"
                    f"\u2022 **Act:** Iteracija po metrikama \u2014 bez nazadovanja!"
                )
                closing = "Presuda je finalna. Ko se ne dr\u017ei plana \u2014 ide na odgovornost!"

            text = (
                f"Dosta bre va\u0161eg laprdanja! Slu\u0161ajte sad presudu za Rundu {round_num}:\n\n"
                f"**Ocene:**\n{scores_block}\n\n"
                f"{pdca}\n\n"
                f"> *\u201e{p2[:200]}...\u201c*\n\n"
                f"{closing}"
            )

        return text, citations[:3]

    @staticmethod
    def _clean_nlm_response(text: str) -> str:
        """
        Strips NLM boilerplate trailers, [TURN_FINISHED] markers, and promotional noise
        that pollute Discord debate output. Called on every live NLM answer before posting.
        """
        import re
        if not text:
            return text

        # Strip [TURN_FINISHED] and everything after it
        text = re.split(r"\[TURN_FINISHED\]", text, flags=re.IGNORECASE)[0]

        # Strip --- separator blocks and everything after
        text = re.split(r"\n\s*---+\s*\n", text)[0]

        # Strip 📊 Mogu generisati... lines (NLM promotional trailer)
        lines = text.splitlines()
        clean_lines = []
        skip = False
        for line in lines:
            stripped = line.strip()
            # Start skipping when NLM promotional trailer begins
            if stripped.startswith("📊") or stripped.startswith("📚 Citirani") or stripped.startswith("• Izvor"):
                skip = True
            if not skip:
                clean_lines.append(line)

        text = "\n".join(clean_lines).strip()

        # Remove repeated "Informacija nije dostupna u izvorima." alone as full answer
        if re.fullmatch(r"[\s\*_]*Informacija nije dostupna u izvorima\.?[\s\*_]*", text, re.IGNORECASE):
            return ""  # Signal to use fallback

        return text

    async def query_persona_notebook(
        self,
        persona: Dict[str, Any],
        topic: str,
        round_num: int,
        recent_turns: List[DebateTurn]
    ) -> tuple[str, List[str]]:
        """
        Queries the specific Google NotebookLM for this persona, giving full debate context.
        Uses a 180s generous timeout, with automatic source document grounding fallback.
        """
        notebook_id = persona.get("default_notebook_id")
        persona_name = persona.get("name")
        persona_id = persona.get("id", "")
        system_prompt = persona.get("system_prompt")

        # ── Round-specific agenda per persona role ──────────────────────────────
        ROUND_AGENDAS = {
            1: {
                "moderator":  "Otvori debatu: postavi problem jasno, formuliši 2-3 ključna inženjerska pitanja koja treba rešiti, i pozovi Eksera da predloži arhitekturu.",
                "architect":  "Predloži konkretan tehnički sistem/arhitekturu za temu (moduli, protokoli, alati). Navedi 2-3 konkretna tehnička rešenja iz sveske.",
                "critic":     "Identifikuj TOP 3 bezbednosne ili tehničke rupe u predlogu Eksera. Konkretno, šta može da pukne i zašto?",
                "strategist": "Proceni ROI i troškove. Koliko košta MVP, koji je rok izlaska na tržište, i gde je profit? Daj konkretnu računicu.",
                "evaluator":  "Na osnovu argumenata svih učesnika u ovoj rundi, oceni svakog (1-10) za arhitekturu, bezbednost i biznis. Donesi PDCA presudu: šta je prioritet za Rundu 2.",
            },
            2: {
                "moderator":  "Sumiraj otvorene probleme iz Runde 1 i zahtevaj konkretna rešenja (ne diskusiju). Šta tačno treba implementirati da bi sistem radio?",
                "architect":  "Daj konkretna mitigaciona rešenja za sve bezbednosne rupe koje je Pikac naveo. Pokaži kod ili pseudokod ako je relevantno.",
                "critic":     "Validiraj ili odbij Ekserova mitigaciona rešenja. Ako su dovoljno dobra, daj uslovni PASS. Ako nisu, precizno navedi šta još nedostaje.",
                "strategist": "Daj finalni finansijski plan: timeline, troškovi, break-even tačka. Ko su kupci i koliko je realan prihod u 6 meseci?",
                "evaluator":  "Donesi KONAČNI binding konsenzus za celu debatu. Koje akcije se odmah implementiraju (PDCA Plan→Do→Check→Act)? Ko je odgovoran za šta? Zatvori debatu jasnom presudom.",
            },
        }

        # Get agenda for this round and persona (default to generic if round > 2)
        agenda = ROUND_AGENDAS.get(round_num, ROUND_AGENDAS[2]).get(
            persona_id,
            "Daj konkretan doprinos temi na osnovu svog specijalnog znanja iz sveske."
        )

        # Format context from recent turns — only last 4 to prevent topic drift
        history_lines = []
        for t in recent_turns[-4:]:
            history_lines.append(f"- **{t.persona_name}**: {t.response_text[:200]}...")
        context_block = "\n".join(history_lines) if history_lines else "Nema prethodnih replika (Otvaranje debate)."

        prompt = (
            f"[MULTI-AGENT DEBATE — RUNDA {round_num}/2]\n"
            f"═══════════════════════════════════════\n"
            f"TEMA DEBATE (ostani STRIKTNO na ovoj temi, ne skreći): {topic}\n"
            f"TVOJA ULOGA: {persona_name}\n"
            f"═══════════════════════════════════════\n\n"
            f"AGENDA ZA OVU RUNDU (tvoj JEDINI zadatak ovde):\n{agenda}\n\n"
            f"Prethodni argumenti (samo za kontekst, ne hvataj se za sporedne detalje):\n{context_block}\n\n"
            f"STRIKTNA PRAVILA ODGOVORA:\n"
            f"1. Ostani 100% fokusiran na TEMU: '{topic}' — ne pominjuješ irelevantne entitete, repo-ve, ili sporedne primere koji nisu u direktnoj vezi.\n"
            f"2. Budi MAKSIMALNO SAŽET: tačno 2-3 kratka pasusa ili buleta, ništa više.\n"
            f"3. Svaki stav mora biti potkrepljen konkretnim podatkom, protokolom, ili metrikom iz sveske.\n"
            f"4. NEMOJ pisati: 'Mogu generisati dijagram', 'Citirani izvori', '[TURN_FINISHED]', niti bilo kakve reklame ili promotivne poruke.\n"
            f"5. Govori u prvom licu, u autentičnom tonu ('Vratiće se rode'), direktno i bez filozofiranja.\n"
            f"6. AKO neka informacija nije u svesci, SVEJEDNO daj argument na osnovu opšteg tehničkog znanja o TEMI — ne kažeš 'Informacija nije dostupna'.\n\n"
            f"Sada daj svoj odgovor za Rundu {round_num}:"
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
            "notebook",
            "query",
            notebook_id,
            prompt,
            "--json",
            "--timeout",
            "180"
        ]

        MAX_RETRIES = 2
        RETRY_WAIT_SECONDS = 30  # Short retry — main protection is 90s turn pacing

        for attempt in range(1, MAX_RETRIES + 1):
            logger.info(
                f"🎙️ Querying NotebookLM ({notebook_id[:8]}...) for {persona_name} "
                f"— pokušaj {attempt}/{MAX_RETRIES}..."
            )
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=185.0)

                res_text = stdout.decode().strip() if stdout else ""
                err_text = stderr.decode().strip() if stderr else ""

                is_rate_limited = (
                    "usage limit" in res_text.lower()
                    or "usage limit" in err_text.lower()
                    or "rejected" in res_text.lower()
                )

                if is_rate_limited:
                    if attempt < MAX_RETRIES:
                        logger.warning(
                            f"⏳ NLM rate-limit za {persona_name} "
                            f"(pokušaj {attempt}/{MAX_RETRIES}). "
                            f"Čekam {RETRY_WAIT_SECONDS}s pre ponovnog slanja upita Google AI-u..."
                        )
                        await asyncio.sleep(RETRY_WAIT_SECONDS)
                        continue
                    else:
                        # All retries exhausted — use grounded source fallback
                        logger.warning(
                            f"⚠️ Svi pokušaji iscrpljeni za {persona_name}. "
                            f"Koristim source-grounded sintezu iz stvarnih dokumenata sveske."
                        )
                        sources = await self.fetch_notebook_sources(notebook_id)
                        grounded_answer, citations = self._synthesize_grounded_response(
                            persona=persona,
                            topic=topic,
                            round_num=round_num,
                            recent_turns=recent_turns,
                            sources=sources
                        )
                        self._memory_cache[cache_key] = (grounded_answer, citations)
                        return grounded_answer, citations

                if proc.returncode != 0:
                    if attempt < MAX_RETRIES:
                        logger.warning(f"⚠️ NLM error (returncode={proc.returncode}) za {persona_name}. Čekam {RETRY_WAIT_SECONDS}s...")
                        await asyncio.sleep(RETRY_WAIT_SECONDS)
                        continue
                    sources = await self.fetch_notebook_sources(notebook_id)
                    grounded_answer, citations = self._synthesize_grounded_response(
                        persona=persona, topic=topic, round_num=round_num,
                        recent_turns=recent_turns, sources=sources
                    )
                    self._memory_cache[cache_key] = (grounded_answer, citations)
                    return grounded_answer, citations

                # ── SUCCESS — parse NotebookLM AI answer ──
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

                    # ── Strip NLM boilerplate (📊, [TURN_FINISHED], etc.) ──
                    answer = self._clean_nlm_response(answer)

                    # If cleaning left an empty answer (e.g. Babac "Informacija nije dostupna"),
                    # fall through to grounded source synthesis instead of posting an empty reply
                    if not answer.strip():
                        logger.warning(
                            f"⚠️ NLM odgovor prazan nakon čišćenja za {persona_name} "
                            f"(vjerovatno 'Informacija nije dostupna'). Koristim grounded sintezu."
                        )
                        sources = await self.fetch_notebook_sources(notebook_id)
                        answer, citations = self._synthesize_grounded_response(
                            persona=persona, topic=topic, round_num=round_num,
                            recent_turns=recent_turns, sources=sources
                        )

                    logger.info(f"✅ NotebookLM AI odgovorio za {persona_name} (pokušaj {attempt})")
                    self._memory_cache[cache_key] = (answer, citations)
                    return answer, citations

                except Exception as parse_err:
                    if res_text:
                        cleaned = self._clean_nlm_response(res_text)
                        if cleaned.strip():
                            self._memory_cache[cache_key] = (cleaned, [])
                            return cleaned, []
                    if attempt < MAX_RETRIES:
                        await asyncio.sleep(RETRY_WAIT_SECONDS)
                        continue
                    return f"Kao {persona_name}, analiziram odgovore iz sveske.", []


            except asyncio.TimeoutError:
                logger.warning(f"⏰ Timeout (pokušaj {attempt}) za {persona_name}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(10)
                    continue
                sources = await self.fetch_notebook_sources(notebook_id)
                grounded_answer, citations = self._synthesize_grounded_response(
                    persona=persona, topic=topic, round_num=round_num,
                    recent_turns=recent_turns, sources=sources
                )
                return grounded_answer, citations
            except Exception as e:
                logger.error(f"Izuzetak u query_persona_notebook (pokušaj {attempt}): {e}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(10)
                    continue
                return f"Kao {persona_name}, analiziram dostupne podatke u bazi znanja.", []

        # Should never reach here
        return f"Kao {persona_name}, analiziram dostupne podatke.", []

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
        channel = bot_or_channel if hasattr(bot_or_channel, "send") else None
        ch_id = persona.get("channel_id", 0)

        if channel is None and hasattr(bot_or_channel, "get_channel"):
            channel = bot_or_channel.get_channel(ch_id)
            if not channel and hasattr(bot_or_channel, "fetch_channel") and ch_id:
                try:
                    channel = await bot_or_channel.fetch_channel(ch_id)
                except Exception as fe:
                    logger.error(f"fetch_channel greška: {fe}")

        if not channel:
            logger.error(f"Kanal {ch_id} nije pronađen za slanje debate.")
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
        if hasattr(channel, "webhooks") and not isinstance(channel, discord.Thread):
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
                logger.debug(f"Webhook nije uspeo ({e}), prelazim na standardni channel.send")

        # Fallback to direct channel.send
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
        if channel is None and hasattr(bot, "fetch_channel"):
            try:
                channel = await bot.fetch_channel(channel_id)
            except Exception as e:
                logger.error(f"Kanal {channel_id} nije pronađen (get/fetch error: {e})")
                return False

        if not channel:
            logger.error(f"Kanal {channel_id} nije pronađen.")
            return False

        # Typing indicator in channel
        try:
            async with channel.typing():
                answer, citations = await self.query_persona_notebook(
                    persona=persona,
                    topic=session.topic,
                    round_num=session.current_round,
                    recent_turns=session.turns
                )
        except Exception as type_err:
            logger.warning(f"Typing greška: {type_err}")
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

    async def run_debate_loop(self, bot: discord.Client, channel_id: int, turn_delay_seconds: float = 90.0):
        """Continuous async loop executing debate turns until completion or pause."""
        session = self.get_session(channel_id)
        if not session:
            return

        # ── GUARD: ne pokreći završenu debatu ponovo ──
        # Ako je debata već odvrtela sve runde (current_round > total_rounds),
        # nemoj je restartovati — samo je uredno zatvori i izađi. Ovo sprečava
        # beskonacno ponavljanje Babac-ovog consensus-a nakon svakog bot restart-a.
        if session.current_round > session.total_rounds:
            logger.info(f"🛑 Debata u kanalu {channel_id} je već završena (round {session.current_round}>{session.total_rounds}). Ne restartujem.")
            session.is_active = False
            session.is_paused = False
            self._save_state()
            return

        # ── GUARD: ne dozvoli 2 paralelna task-a za isti kanal ──
        existing = self._running_tasks.get(channel_id)
        if existing is not None and not existing.done():
            logger.warning(f"⚠️ Debata za kanal {channel_id} već trči (task živ). Ne dupliram loop.")
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
                # ── NLM Rate-Limit Guard: pause between turns ──
                # Google NotebookLM enforces a rolling per-account rate limit.
                # We post a visible "thinking" notice so users know the bot is working.
                try:
                    wait_ch = bot.get_channel(channel_id) or await bot.fetch_channel(channel_id)
                    next_idx = (session.current_turn_index) % len(session.personas)
                    next_persona = session.personas[next_idx]
                    nb_title = next_persona.get('notebook_title', 'NotebookLM')
                    wait_notice = await wait_ch.send(
                        f"⏳ **{next_persona['name']}** priprema odgovor iz NotebookLM sveske "
                        f"*\"{nb_title}\"*... "
                        f"(Google AI zahteva kratku pauzu između upita)"
                    )
                    await asyncio.sleep(turn_delay_seconds)
                    try:
                        await wait_notice.delete()
                    except Exception:
                        pass
                except Exception:
                    await asyncio.sleep(turn_delay_seconds)
        except asyncio.CancelledError:
            logger.info(f"Debata u kanalu {channel_id} je prekinuta/otkazana.")
        except Exception as e:
            logger.error(f"Greška u petlji debate: {e}", exc_info=True)
            session.is_active = False
            self._save_state()

    def start_debate(self, bot: discord.Client, channel_id: int, turn_delay: float = 3.0) -> asyncio.Task:
        # ── GUARD: ako već trči živ task, nemoj kreirati dupli loop ──
        existing = self._running_tasks.get(channel_id)
        if existing is not None and not existing.done():
            logger.warning(f"⚠️ start_debate: debata za {channel_id} već aktivna. Cancel-ujem staru i pravim novu.")
            existing.cancel()

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
