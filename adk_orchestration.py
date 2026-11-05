#!/usr/bin/env python3
"""
adk_orchestration.py — Google ADK 2.0 Dynamic Multi-Agent Orchestration Engine.
==============================================================================
Pravila:
  1. Miki Nosonja (Orchestrator) prima korisnički upit i postavlja
     tačno to pitanje Google NotebookLM svesci (3bd81caf-9396-4593-ad18-4a98dc1a2115).
  2. Čeka stvarni odgovor od NotebookLM-a. Nema lokalnog traženja niti nagađanja.
     Ako NotebookLM ne može da se dohvati ili pukne -> ODMAH GREŠKA i prekid.
  3. Na osnovu odgovora iz sveske, Miki Nosonja organizuje tim agenata, dodeljuje im uloge,
     promptove i instrukcije.
  4. Agenti primarno koriste Cloud Ollama sa failoverom na zvanični Gemini CLI (gemini-3.5-flash-lite u sandbox okruženju).
  5. Nema statičnih, unapred hardkodovanih persona.
"""

import os
import sys
import json
import re
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, AsyncGenerator
from dataclasses import dataclass
from pathlib import Path

from google.adk.agents import BaseAgent, LoopAgent, SequentialAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext

from gemini_client import query_gemini_cli, query_ollama_cloud, query_llm
from agy_client import query_agy_cli
from a2tools_runtime import tools_runtime, ORCHESTRATION_NOTEBOOK_ID
from src.services.sprint_booster_service import SprintBoosterService

logger = logging.getLogger("ADKOrchestration")


def sanitize_adk_identifier(name: str) -> str:
    """Osigurava da je ime agenta validan Python identifikator za Google ADK 2.0 BaseAgent."""
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', name).strip('_')
    if not cleaned or not cleaned[0].isalpha():
        cleaned = f"Agent_{cleaned}".strip('_')
    return cleaned


# ── 1. DYNAMIC AGENT REPRESENTATION ──────────────────────────────────────────

class DynamicWorkerAgent(BaseAgent):
    """
    Radni agent čiju ulogu i prompt dinamički kreira Miki Nosonja
    na osnovu odgovora iz NotebookLM-a.
    Izvršava poziv preko Cloud Ollama uz automatski failover na Gemini CLI (gemini-3.5-flash-lite).
    """

    instruction: str = ""
    output_key: str = "agent_output"

    def __init__(
        self,
        name: str,
        instruction: str,
        output_key: str = "agent_output",
        description: str = "",
    ):
        super().__init__(name=name, description=description)
        self.instruction = instruction
        self.output_key = output_key

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        user_task = ctx.session.state.get("user_task", "")
        notebook_knowledge = ctx.session.state.get("notebook_knowledge", "")
        previous_outputs = ctx.session.state.get("shared_workspace", "")

        booster_service = ctx.session.state.get("sprint_booster_service")
        if not booster_service:
            booster_service = SprintBoosterService()

        prompt_payload = (
            f"Korisnički zadatak:\n{user_task}\n\n"
            f"Znanje iz Google NotebookLM sveske:\n{notebook_knowledge}\n\n"
        )
        if previous_outputs:
            prompt_payload += f"Prethodni rad drugih agenata:\n{previous_outputs}\n\n"

        prompt_payload += f"Tvoj zadatak ({self.name}): Izvrši svoj deo u skladu sa tvojom instrukcijom."

        # Token Pruning preko SprintBoosterService
        prompt_payload = booster_service.optimize_prompt(prompt_payload)

        logger.info(f"[{self.name}] Izvršavam dodeljeni zadatak preko Cloud Ollama / Gemini CLI...")
        loop = asyncio.get_running_loop()

        # Non-blocking poziv modela sa rotacijom i Cloud Ollama prioritetom
        result = await loop.run_in_executor(
            None,
            lambda: query_llm(
                prompt=prompt_payload,
                system=self.instruction,
                prefer_cloud_ollama=True,
                timeout=120
            )
        )

        ctx.session.state[self.output_key] = result
        
        # Store-by-Reference: skladišti pun izlaz i prosleđuje sažeti izvod u shared workspace
        summary_relay = booster_service.process_agent_output(self.name, result)
        
        existing = ctx.session.state.get("shared_workspace", "")
        ctx.session.state["shared_workspace"] = (
            f"{existing}\n\n{summary_relay}"
        ).strip()

        yield Event(author=self.name)


# ── 2. MIKI NOSONJA ORCHESTRATOR ─────────────────────────────────────────────

class MikiNosonjaOrchestrator:
    """
    Glavni organizator (Miki Nosonja):
    1. Šalje korisnikov upit direktno Google NotebookLM-u (3bd81caf-9396-4593-ad18-4a98dc1a2115).
    2. Čeka odgovor. Ako nema odgovora -> baca Fatal Error (nema lokalnog nagađanja).
    3. Koristeći Gemini CLI i nalaze iz sveske, dodeljuje timu uloge i promptove.
    4. Pokreće orkestraciju.
    """

    def __init__(self, notebook_id: str = ORCHESTRATION_NOTEBOOK_ID):
        self.notebook_id = notebook_id

    async def ask_notebooklm(self, user_task: str) -> str:
        """
        Postavlja tačno korisničko pitanje u Google NotebookLM i čeka odgovor.
        """
        logger.info(f"[Miki Nosonja] Šaljem korisničko pitanje NotebookLM svesci {self.notebook_id}...")
        
        # Šalje se tačno ono što je korisnik tražio
        res = await tools_runtime.query_notebooklm(
            notebook_id=self.notebook_id,
            query=user_task,
            timeout=180.0
        )

        if not res.success or res.is_error:
            err_msg = (
                f"FATALNA GREŠKA: Miki Nosonja nije uspeo da dobije odgovor od Google NotebookLM sveske "
                f"({self.notebook_id}): {res.output}\n"
                "Sistem je momentalno zaustavljen jer je lokalno nagađanje strogo zabranjeno."
            )
            logger.error(err_msg)
            raise RuntimeError(err_msg)

        logger.info(f"[Miki Nosonja] Uspešno dobijen odgovor od NotebookLM ({len(res.output)} karaktera).")
        return res.output

    async def distribute_roles(self, user_task: str, notebook_knowledge: str) -> List[Dict[str, str]]:
        """
        Miki Nosonja koristi Gemini CLI da na osnovu odgovora iz sveske organizuje
        agente i svakom upiše ulogu, prompt i sistemske instrukcije.
        """
        logger.info("[Miki Nosonja] Dodeljujem uloge i upisujem promptove agentima...")

        distribution_prompt = (
            f"Ti si Miki Nosonja (glavni organizator). Korisnik je tražio sledeće:\n"
            f"'{user_task}'\n\n"
            f"Evo tačnog odgovora i znanja iz Google NotebookLM sveske:\n"
            f"{notebook_knowledge}\n\n"
            f"Tvoj zadatak je da na osnovu ovog odgovora iz sveske organizuješ tim agenata:\n"
            f"1. Odredi koji su agenti potrebni (npr. Agent za Analizu/Istraživanje, Agent za Implementaciju/Kod, Agent za Verifikaciju).\n"
            f"2. Svakom agentu dodeli precizno ime, ulogu i napiši kompletnu sistemsku instrukciju (prompt).\n"
            f"Odgovori ISKLJUČIVO u validnom JSON formatu kao lista objekata:\n"
            "[\n"
            '  {"name": "...", "role": "...", "instruction": "..."},\n'
            '  {"name": "...", "role": "...", "instruction": "..."}\n'
            "]\n"
            "Nemoj dodavati nikakav uvodni tekst ni markdown blokove izvan čistog JSON-a."
        )

        loop = asyncio.get_running_loop()
        try:
            raw_json = await loop.run_in_executor(
                None,
                lambda: query_agy_cli(
                    prompt=distribution_prompt,
                    system="Ti si Miki Nosonja. Vrati ISKLJUČIVO validan JSON niz sa ulogama i instrukcijama.",
                    timeout=150
                )
            )
        except Exception as agy_err:
            logger.warning(f"[Miki Nosonja] agy CLI raspodela nije uspela ({agy_err}), prelazim na Cloud Ollama fallback...")
            raw_json = await loop.run_in_executor(
                None,
                lambda: query_llm(
                    prompt=distribution_prompt,
                    system="Ti si Miki Nosonja. Vrati ISKLJUČIVO validan JSON niz sa ulogama i instrukcijama.",
                    prefer_cloud_ollama=True,
                    timeout=90
                )
            )

        agents_data = []
        try:
            match = re.search(r"\[.*\]", raw_json, re.DOTALL)
            if match:
                agents_data = json.loads(match.group(0))
        except Exception as e:
            logger.warning(f"[Miki Nosonja] JSON parsiranje uloga nije uspelo ({e}). Pravim direktnu raspodelu.")

        if not agents_data:
            # Deterministička podela na bazi sveske ako JSON nije bio čist
            agents_data = [
                {
                    "name": "Istrazivac",
                    "role": "Analiza zahteva i izdvajanje činjenica iz sveske",
                    "instruction": f"Ti si agent za analizu. Na osnovu znanja iz NotebookLM:\n{notebook_knowledge[:1000]}\nIstraži i pripremi činjenice za zadatak: '{user_task}'."
                },
                {
                    "name": "Graditelj",
                    "role": "Konstrukcija i sinteza rešenja",
                    "instruction": f"Ti si agent za izgradnju. Na osnovu nalaza iz sveske implementiraj kompletno rešenje za zadatak: '{user_task}'."
                }
            ]

        # Sanitizacija imena agenata za Google ADK 2.0 BaseAgent
        sanitized_roles = []
        for a in agents_data:
            raw_name = a.get("name", "Agent")
            clean_name = sanitize_adk_identifier(raw_name)
            sanitized_roles.append({
                "name": clean_name,
                "display_name": raw_name,
                "role": a.get("role", "Radni agent"),
                "instruction": a.get("instruction", "")
            })

        logger.info(f"[Miki Nosonja] Dodeljeno ukupno {len(sanitized_roles)} agenata.")
        return sanitized_roles

    async def execute_orchestration(
        self,
        user_task: str,
        on_event_callback: Optional[Callable[[str, str], Any]] = None
    ) -> Dict[str, Any]:
        """
        Kompletan tok:
        1. Miki Nosonja postavlja pitanje NotebookLM-u i ČEKA ODGOVOR.
        2. Dodeljuje uloge i promptove.
        3. Radni agenti izvršavaju zadatak preko Cloud Ollama / agy sa rotacijom.
        4. Vraća finalni sintetizovani izlaz.
        """
        # Korak 1: Postavljanje pitanja svesci i čekanje odgovora
        if on_event_callback:
            await on_event_callback(
                "Miki Nosonja (Orchestrator)",
                f"📨 Postavljam pitanje Google NotebookLM svesci (`{self.notebook_id}`):\n"
                f"> *„{user_task}“*\n"
                f"⏳ Čekam odgovor iz baze znanja..."
            )

        notebook_knowledge = await self.ask_notebooklm(user_task)

        if on_event_callback:
            preview = notebook_knowledge[:350] + "..." if len(notebook_knowledge) > 350 else notebook_knowledge
            await on_event_callback(
                "Miki Nosonja (Orchestrator)",
                f"📖 **Odgovor iz Google NotebookLM sveske primljen:**\n{preview}\n\n"
                f"⚙️ Organizujem uloge i upisujem promptove za agente..."
            )

        # Korak 2: Raspodela uloga i promptova
        assigned_roles = await self.distribute_roles(user_task, notebook_knowledge)

        if on_event_callback:
            role_lines = "\n".join([f"• **{r['name']}** ({r['role']})" for r in assigned_roles])
            await on_event_callback(
                "Miki Nosonja (Orchestrator)",
                f"👥 **Agenti su raspoređeni sa instrukcijama:**\n{role_lines}\n\n"
                f"🚀 Pokrećem Cloud Ollama / Agy izvršavanje..."
            )

        # Korak 3: Kreiranje radnih agenata i izvršavanje
        booster_service = SprintBoosterService(session_id=f"session_{abs(hash(user_task))}")
        state: Dict[str, Any] = {
            "user_task": user_task,
            "notebook_knowledge": notebook_knowledge,
            "shared_workspace": "",
            "sprint_booster_service": booster_service,
        }

        class SessionWrapper:
            def __init__(self, s): self.state = s
        class CtxWrapper:
            def __init__(self, sess): self.session = sess

        ctx = CtxWrapper(SessionWrapper(state))
        agent_outputs: Dict[str, str] = {}

        for role_spec in assigned_roles:
            agent_name = role_spec.get("name", "Agent")
            display_name = role_spec.get("display_name", agent_name)
            agent_instruction = role_spec.get("instruction", "")
            agent_role = role_spec.get("role", "")

            if on_event_callback:
                await on_event_callback(display_name, f"⚡ Preuzimam zadatak: *{agent_role}*...")

            worker = DynamicWorkerAgent(
                name=agent_name,
                instruction=agent_instruction,
                output_key=f"output_{agent_name}",
                description=agent_role
            )

            async for _ in worker._run_async_impl(ctx):
                pass

            out = state.get(f"output_{agent_name}", "")
            agent_outputs[agent_name] = out

            if on_event_callback:
                out_preview = out[:400] + "..." if len(out) > 400 else out
                await on_event_callback(display_name, f"✅ Završeno:\n{out_preview}")

        # Finalna sinteza od strane Mikija Nosonje
        nb_summary = notebook_knowledge if len(notebook_knowledge) <= 12000 else notebook_knowledge[:12000] + "\n...(izvod iz baze znanja)..."
        synthesis_prompt = (
            f"Korisnik je postavio zadatak: '{user_task}'\n\n"
            f"Znanje iz NotebookLM sveske:\n{nb_summary}\n\n"
            f"Radovi agenata:\n{state['shared_workspace']}\n\n"
            f"Kao Miki Nosonja, daj konačan, sažet, direktan i 100% inženjerski tačan odgovor za korisnika."
        )

        loop = asyncio.get_running_loop()
        try:
            final_answer = await loop.run_in_executor(
                None,
                lambda: query_agy_cli(
                    prompt=synthesis_prompt,
                    system="Ti si Miki Nosonja. Daj konačan, udaran i inženjerski precizan rezime rada agenata.",
                    timeout=150
                )
            )
        except Exception as agy_err:
            logger.warning(f"[Miki Nosonja] agy CLI sinteza nije uspela ({agy_err}), prelazim na Cloud Ollama fallback...")
            final_answer = await loop.run_in_executor(
                None,
                lambda: query_llm(
                    prompt=synthesis_prompt,
                    system="Ti si Miki Nosonja. Daj konačan, udaran i inženjerski precizan rezime rada agenata.",
                    prefer_cloud_ollama=True,
                    timeout=100
                )
            )

        if on_event_callback:
            await on_event_callback("Miki Nosonja (Konačni Odgovor)", f"🏆 **Konačno Rešenje:**\n{final_answer}")

        return {
            "success": True,
            "user_task": user_task,
            "notebook_knowledge": notebook_knowledge,
            "agent_outputs": agent_outputs,
            "final_answer": final_answer
        }


# Singleton manager
adk_manager = MikiNosonjaOrchestrator()
