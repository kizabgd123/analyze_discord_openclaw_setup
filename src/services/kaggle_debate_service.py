#!/usr/bin/env python3
"""
kaggle_debate_service.py — 2-Round Grounded Multi-Agent Debate for Kaggle.
==========================================================================
Strict Security & Grounding Policy:
  - NotebookLM sources filtered natively via --source-ids flag.
  - Minimal 2-round debate protocol:
      Round 1: Opening positions (Strategist, Engineer, Skeptic).
      Round 2: Cross-examination (Each agent directly addresses the others' points).
  - Synthesis logs agreed plan, unresolved disagreements, and deciding rationale.
  - Generates standalone runnable code saved to fixed path:
      artifacts/kaggle/<competition>/pipeline.py
  - Enforces [EKSPERIMENT: <hipoteza>] label until remote validation runs.
"""

import os
import re
import json
import hashlib
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from a2tools_runtime import tools_runtime, ORCHESTRATION_NOTEBOOK_ID
from src.services.kaggle_service import kaggle_service, KaggleCompetitionContext
from gemini_client import query_llm

logger = logging.getLogger("KaggleDebateService")

ARTIFACTS_DIR = Path("/home/kizamladjanijebac/Desktop/discord-openclaw/artifacts/kaggle")

OFFICIAL_COMPETITION_METADATA = {
    "name-that-llm": {
        "classes": sorted([
            "claude-fable-5", "claude-opus-4-6", "claude-opus-4-8", "claude-opus-5", "claude-sonnet-5",
            "gemini-3.1-pro-preview", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash",
            "glm-5.3", "glm-5.3-flash",
            "gpt-5.5", "gpt-5.6-luna", "gpt-5.6-sol", "gpt-5.6-terra", "gpt-6-astra",
            "kimi-k3", "qwen3.8-max"
        ]),
        "input_pattern": "next(p for p in ['/kaggle/input/competitions/name-that-llm', '/kaggle/input/name-that-llm'] if os.path.exists(p + '/train.csv'))",
        "output_format": "submission.parquet (columns: id, model)",
    }
}


def filter_competition_sources(
    sources: List[Dict[str, Any]], competition: str
) -> List[Dict[str, Any]]:
    """Filters NotebookLM sources by competition slug to prevent cross-competition mixing."""
    if not sources:
        return []

    comp_lower = competition.lower()
    filtered = []

    if "name-that-llm" in comp_lower:
        for s in sources:
            title = s.get("title", "").lower()
            if "gemma" in title:
                continue
            if any(k in title for k in ["name that llm", "report", "pool", "author", "prism", "honest", "who am i"]):
                filtered.append(s)
    elif "gemma" in comp_lower:
        for s in sources:
            title = s.get("title", "").lower()
            if "gemma" in title:
                filtered.append(s)
    else:
        # Fallback to all sources if not a known multi-competition notebook entry
        filtered = list(sources)

    return filtered if filtered else sources


class KaggleDebateService:
    """Orchestrates 2-round multi-agent debate grounded in competition sources."""

    def __init__(self, notebook_id: str = ORCHESTRATION_NOTEBOOK_ID):
        self.notebook_id = notebook_id

    async def run_debate(
        self,
        competition: str,
        on_event_callback: Optional[Callable[[str, str], Any]] = None,
    ) -> Dict[str, Any]:
        """Executes full 2-round debate and outputs pipeline plan + code artifact."""
        comp = kaggle_service.validate_slug(competition)

        # 1. Fetch sources and filter by competition
        if on_event_callback:
            await on_event_callback(
                "Moderator",
                f"🔍 Filtriram izvore u NotebookLM svesci (`{self.notebook_id}`) za takmičenje `{comp}`...",
            )

        all_sources = await tools_runtime.list_notebook_sources(self.notebook_id)
        comp_sources = filter_competition_sources(all_sources, comp)
        source_ids = [s["id"] for s in comp_sources if "id" in s]

        logger.info(
            f"Filtered {len(comp_sources)}/{len(all_sources)} sources for competition {comp}"
        )

        # 2. Fetch live Kaggle telemetry
        ctx: KaggleCompetitionContext = await kaggle_service.get_competition_context(comp)

        # 3. Grounded query to NotebookLM with strict source IDs
        if on_event_callback:
            await on_event_callback(
                "Moderator",
                f"📖 Postavljam ciljani upit NotebookLM svesci sa restrikcijom na {len(source_ids)} izvora...",
            )

        grounding_query = (
            f"Za takmičenje {comp}, navedi ključna pravila, evaluacionu metriku, "
            f"hardverska ograničenja, offline zahteve i verifikovane arhitekture. "
            f"Citiraj tačne izvore."
        )

        nlm_res = await tools_runtime.query_notebooklm(
            notebook_id=self.notebook_id,
            query=grounding_query,
            timeout=150.0,
            source_ids=source_ids if source_ids else None,
        )

        if not nlm_res.success or nlm_res.is_error:
            raise RuntimeError(f"Neuspešno dohvatanje NotebookLM znanja: {nlm_res.output}")

        knowledge = nlm_res.output

        # Context telemetry header
        telemetry_header = (
            f"TAKMIČENJE: {comp}\n"
            f"Istorijski LB rekord korisnika: {ctx.best_score or 'N/A'} (datum: {ctx.best_date or 'N/A'})\n"
            f"Poslednji LB skor korisnika: {ctx.latest_score or 'N/A'} (datum: {ctx.latest_date or 'N/A'})\n"
            f"Preostalo dnevnih submisija: {ctx.remaining_today}\n"
            f"Ograničenja iz sveske:\n{knowledge[:4000]}\n"
        )

        # ── ROUND 1: OPENING POSITIONS ──
        if on_event_callback:
            await on_event_callback("Moderator", "🎙️ **Runda 1: Otvaranje pozicija (Strateg, Inženjer, Skeptik)**")

        loop = asyncio.get_running_loop()

        # Strategist
        strategist_p = (
            f"{telemetry_header}\n"
            "Ti si Strateg. Na osnovu metrike i pravila takmičenja, predloži strateški cilj, "
            "fokus modela i vremenski budžet. Budi sažet i direktan."
        )
        strat_r1 = await loop.run_in_executor(
            None,
            lambda: query_llm(
                prompt=strategist_p,
                system="Ti si Kaggle Grandmaster Strateg. Fokusiraj se na metriku i optimizacioni cilj.",
                prefer_cloud_ollama=True,
                timeout=60,
            ),
        )
        if on_event_callback:
            await on_event_callback("Strateg (Runda 1)", strat_r1)

        # Engineer
        engineer_p = (
            f"{telemetry_header}\n"
            f"Strateg predlaže: {strat_r1}\n"
            "Ti si Inženjer. Predloži konkretan Python pipeline (preprocessing, model ensemble, "
            "submission format). Navedi tačne nazive modela i biblioteka."
        )
        eng_r1 = await loop.run_in_executor(
            None,
            lambda: query_llm(
                prompt=engineer_p,
                system="Ti si Kaggle ML Inženjer. Fokusiraj se na izvodljiv kod, preprocesiranje i ensemble.",
                prefer_cloud_ollama=True,
                timeout=60,
            ),
        )
        if on_event_callback:
            await on_event_callback("Inženjer (Runda 1)", eng_r1)

        # Skeptic
        skeptic_p = (
            f"{telemetry_header}\n"
            f"Strateg predlaže: {strat_r1}\n"
            f"Inženjer predlaže: {eng_r1}\n"
            "Ti si Skeptik. Iznesi tačne rizike curenja podataka (leakage), memorijska preopterećenja, "
            "rizik prekoračenja 9h limita i kršenja offline pravila."
        )
        skep_r1 = await loop.run_in_executor(
            None,
            lambda: query_llm(
                prompt=skeptic_p,
                system="Ti si Nemilosrdni Kaggle Skeptik. Pronađi svaku slabost i rizik diskvalifikacije.",
                prefer_cloud_ollama=True,
                timeout=60,
            ),
        )
        if on_event_callback:
            await on_event_callback("Skeptik (Runda 1)", skep_r1)

        # ── ROUND 2: CROSS-EXAMINATION ──
        if on_event_callback:
            await on_event_callback("Moderator", "⚔️ **Runda 2: Unakrsna debata i rešavanje prigovora**")

        # Engineer responds to Skeptic
        eng_r2_p = (
            f"{telemetry_header}\n"
            f"Skeptik je uložio sledeće prigovore:\n{skep_r1}\n\n"
            "Kao Inženjer, odgovori tačno na svaki prigovor Skeptika. "
            "Kako tačno rešavaš rizik curenja podataka i memorijska ograničenja?"
        )
        eng_r2 = await loop.run_in_executor(
            None,
            lambda: query_llm(
                prompt=eng_r2_p,
                system="Ti si Inženjer. Brani i adaptiraj rešenje odgovarajući na konkretne primedbe Skeptika.",
                prefer_cloud_ollama=True,
                timeout=60,
            ),
        )
        if on_event_callback:
            await on_event_callback("Inženjer (Runda 2)", eng_r2)

        # Strategist arbitrates and decides
        strat_r2_p = (
            f"{telemetry_header}\n"
            f"Inženjer: {eng_r2}\n"
            f"Skeptik: {skep_r1}\n"
            "Kao Strateg, donesi konačnu arbitražu. Koji kompromisi se prihvataju? "
            "Zabeleži tačne tačke neslaganja i razlog tvoje odluke."
        )
        strat_r2 = await loop.run_in_executor(
            None,
            lambda: query_llm(
                prompt=strat_r2_p,
                system="Ti si Glavni Strateg. Donesi konačnu odluku i objasni odlučujući razlog.",
                prefer_cloud_ollama=True,
                timeout=60,
            ),
        )
        if on_event_callback:
            await on_event_callback("Strateg (Runda 2 - Odluka)", strat_r2)

        # ── SYNTHESIS & CODE GENERATION ──
        if on_event_callback:
            await on_event_callback("Moderator", "📝 **Generišem konačni plan i Python pipeline skriptu...**")

        synth_p = (
            f"{telemetry_header}\n"
            f"Runda 1 Inženjer: {eng_r1}\n"
            f"Runda 1 Skeptik: {skep_r1}\n"
            f"Runda 2 Reakcija Inženjera: {eng_r2}\n"
            f"Runda 2 Odluka Strata: {strat_r2}\n\n"
            "Sintetizuj konačan plan za korisnika:\n"
            "1. Naslov i hipoteza eksperimenta [EKSPERIMENT: <hipoteza>]\n"
            "2. Ključne dogovorene komponente pipeline-a\n"
            "3. Zabeležena neslaganja i razlog konačne odluke\n"
            "4. Status validacije: 'STATUS: NOT RUN (Čeka se pokretanje na Kaggle compute-u)'\n"
            "Nemoj pisati kod u ovom tekstu, kod će biti u fajlu."
        )
        plan_summary = await loop.run_in_executor(
            None,
            lambda: query_llm(
                prompt=synth_p,
                system="Ti si Moderator. Sažmi plan objektivno, sa jasnim oznakama eksperimenta i neslaganja.",
                prefer_cloud_ollama=True,
                timeout=80,
            ),
        )

        # Generate standalone code script
        meta_info = OFFICIAL_COMPETITION_METADATA.get(comp, {})
        classes_str = json.dumps(meta_info.get("classes", []))
        input_pattern = meta_info.get("input_pattern", "/kaggle/input/" + comp)

        code_p = (
            f"Takmičenje: {comp}\n"
            f"Zvanične Klase Takmičenja (MORA BITI TAČNO OVIH 18 BEZ PROMENA I BEZ HALUCINACIJA):\n{classes_str}\n\n"
            f"Putanja do ulaza:\n{input_pattern}\n\n"
            f"Znanje o takmičenju:\n{knowledge[:3000]}\n"
            f"Dogovorena arhitektura:\n{eng_r2}\n\n"
            "Napiši KOMPLETNU, samostalnu Python skriptu za offline evaluaciju i inferencu. "
            "Skripta mora čitati ulaze iz /kaggle/input, primeniti modele i upisati /kaggle/working/submission.parquet sa kolonama 'id' i 'model'. "
            "Za mapiranje labela koristi ISKLJUČIVO zvanične klase navedene iznad. "
            "Vrati ISKLJUČIVO čist Python kod unutar ```python ... ``` bloka bez pratećeg ćaskanja."
        )
        raw_code = await loop.run_in_executor(
            None,
            lambda: query_llm(
                prompt=code_p,
                system="Ti si Python AI Expert. Vrati samo validan Python kod spreman za izvršenje na Kaggle.",
                prefer_cloud_ollama=True,
                timeout=100,
            ),
        )

        code_match = re.search(r"```python\s*(.*?)\s*```", raw_code, re.DOTALL)
        clean_code = code_match.group(1).strip() if code_match else raw_code.strip()

        # Save code to fixed artifact path
        comp_dir = ARTIFACTS_DIR / comp
        comp_dir.mkdir(parents=True, exist_ok=True)
        code_file = comp_dir / "pipeline.py"
        code_file.write_text(clean_code, encoding="utf-8")

        sha256 = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()

        if on_event_callback:
            await on_event_callback(
                "Moderator (Konačni Plan)",
                f"📋 **Konačni Plan Debatnog Tima:**\n{plan_summary}\n\n"
                f"💾 **Pipeline kod generisan:** `{code_file}`\n"
                f"🔑 **SHA-256:** `{sha256}`\n"
                f"⚠️ **Validacija**: Nije pokrenuta na Kaggle compute (`STATUS: NOT RUN`). Označeno kao `[EKSPERIMENT]`.",
            )

        return {
            "success": True,
            "competition": comp,
            "plan_summary": plan_summary,
            "code_path": str(code_file),
            "sha256": sha256,
            "total_submissions": ctx.total_submissions,
            "best_score": ctx.best_score,
            "latest_score": ctx.latest_score,
            "remaining_today": ctx.remaining_today,
            "status": "NOT RUN",
            "experiment_tag": True,
        }


kaggle_debate_service = KaggleDebateService()
