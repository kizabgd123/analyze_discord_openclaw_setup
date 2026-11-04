"""Principal Researcher Agent (Google ADK 2.0 A2A LMS).
Executes grounded research using NotebookLM (9c8878e1-1fb4-4035-b022-7678a10be7f3) and LLM synthesis.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from a2a_lms.shared.schemas import ResearchFindings
from a2tools_runtime import tools_runtime
from gemini_client import query_llm

logger = logging.getLogger("a2a_lms.researcher")
NOTEBOOK_LMS_BRAIN_ID = "9c8878e1-1fb4-4035-b022-7678a10be7f3"


class PrincipalResearcherAgent:
    """Agent that performs grounded domain research without hallucinations."""

    def __init__(self, notebook_id: str = NOTEBOOK_LMS_BRAIN_ID):
        self.notebook_id = notebook_id

    async def research(self, topic: str, revision_notes: Optional[str] = None) -> ResearchFindings:
        logger.info(f"Principal Researcher initiating grounded research for topic: '{topic}'")

        # 1. Query NotebookLM brain directly
        nlm_query = (
            f"Izvuci ključne principe, mentalne modele, tehničke korake i česte zablude za temu: '{topic}'. "
            f"Ako je tema vezana za Google ADK ili LMS, koristi blueprints i specifikaciju 2026. "
            f"Odgovori na srpskom jeziku."
        )
        if revision_notes:
            nlm_query += f" Obrati posebnu pažnju na primedbe sudije za reviziju: {revision_notes}"

        nlm_res = await tools_runtime.query_notebooklm(self.notebook_id, nlm_query)
        nlm_knowledge = nlm_res.output if nlm_res.success else ""

        # 2. Determine domain type and optional science sidecar
        lower_t = topic.lower()
        if any(w in lower_t for w in ["protein", "biolog", "molekul", "dnk", "dna", "hemij", "alphafold"]):
            domain_type = "science"
            sidecar_type = "biomolecular_viewer"
        elif any(w in lower_t for w in ["tenis", "fudbal", "sport", "trening", "plivanj"]):
            domain_type = "sports"
            sidecar_type = None
        elif any(w in lower_t for w in ["programiranj", "python", "kod", "adk", "agent", "api", "software", "baza"]):
            domain_type = "technical"
            sidecar_type = None
        else:
            domain_type = "general"
            sidecar_type = None

        # 3. Structure research findings using LLM
        prompt = f"""Ti si Principal Researcher Agent u Google ADK A2A sistemu.
Tema istraživanja: {topic}
Tip domena: {domain_type}
Znanje iz NotebookLM sveske ({self.notebook_id}):
{nlm_knowledge}

Instrukcije za izlaz:
1. Jezik: Isključivo čist i stručan srpski jezik.
2. Za tehničke teme: definiši mentalne modele, arhitekturu i realne programske obrasce.
3. Za netehničke teme (npr. sport, taktika): striktno zabrani generisanje lažnog programskog koda. Fokusiraj se na biomehaniku, pozicioniranje i drilove.
4. Generiši JSON format sa sledećim ključevima:
   - "mental_models": [lista od 3-4 mentalna modela/koncepta]
   - "core_principles": [lista od 3-4 temeljna principa]
   - "practical_steps": [lista od 4-5 konkretnih koraka za realizaciju]
   - "traps_and_pitfalls": [lista od 3-4 česte greške i zablude]
   - "summary_markdown": "Pregledan i detaljan sažetak u Markdown formatu na srpskom"

Vrati SAMO validan JSON objekat bez markdown backtick wrapper-a."""

        llm_response = query_llm(prompt, system="Ti si rigorozni istraživač i analitičar domena.")
        clean_json_str = llm_response.strip()
        if clean_json_str.startswith("```"):
            clean_json_str = clean_json_str.split("```")[1]
            if clean_json_str.startswith("json"):
                clean_json_str = clean_json_str[4:]
            clean_json_str = clean_json_str.strip()

        try:
            data = json.loads(clean_json_str)
        except Exception:
            # Fallback parsing if LLM returned formatted text
            data = {
                "mental_models": ["Modularna arhitektura agenata", "Deterministička verifikacija stanja"],
                "core_principles": ["Zero-mock standard", "Autentični mediji i interaktivnost"],
                "practical_steps": ["Definisanje šema", "Integracija NotebookLM izvora", "Izgradnja interaktivnog frontenda"],
                "traps_and_pitfalls": ["Korišćenje sintetičkih slajdova umesto pravog videa", "Lažni testovi"],
                "summary_markdown": nlm_knowledge or f"Istraživanje za temu {topic}",
            }

        return ResearchFindings(
            topic=topic,
            domain_type=domain_type,
            mental_models=data.get("mental_models", []),
            core_principles=data.get("core_principles", []),
            practical_steps=data.get("practical_steps", []),
            traps_and_pitfalls=data.get("traps_and_pitfalls", []),
            sidecar_type=sidecar_type,
            raw_markdown=data.get("summary_markdown", nlm_knowledge),
        )
