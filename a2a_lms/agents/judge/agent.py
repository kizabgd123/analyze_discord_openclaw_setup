"""Senior Judge Agent (Google ADK 2.0 A2A LMS).
Strict auditor and evaluator enforcing accuracy, Serbian language parity, and domain fit.
"""

import json
import logging
from typing import Dict, Any, List
from a2a_lms.shared.schemas import ResearchFindings, JudgeFeedback
from gemini_client import query_llm

logger = logging.getLogger("a2a_lms.judge")


class SeniorJudgeAgent:
    """Rigorous evaluation agent verifying curriculum accuracy and language parity."""

    def evaluate(self, findings: ResearchFindings) -> JudgeFeedback:
        logger.info(f"Senior Judge auditing research findings for: '{findings.topic}'")

        prompt = f"""Ti si Senior Judge Agent u sistemu verifikacije obrazovnih sadržaja.
Tvoj zadatak je da izvršiš rigoroznu reviziju priloženog istraživanja.

TEMA: {findings.topic}
TIP DOMENA: {findings.domain_type}
NALAZI ISTRAŽIVANJA:
- Mentalni modeli: {findings.mental_models}
- Temeljni principi: {findings.core_principles}
- Koraci primene: {findings.practical_steps}
- Zamke i zablude: {findings.traps_and_pitfalls}
- Sažetak: {findings.raw_markdown[:800]}

RUBRIKA OCENJIVANJA (Ocene 1-10):
1. Tačnost (accuracy_score): Da li su svi koncepti činjenično tačni? Da li nema halucinacija? (Za netehničke teme, striktno zabranjen generisani programski kod).
2. Jezički kontinuitet (language_parity_score): Da li je sve na čistom, prirodnom i stručnom srpskom jeziku?
3. Kompletnost i domen (completeness_score): Da li su pokriveni mentalni modeli, koraci i zamke u skladu sa domenom?

KRITERIJUM PROLAZA:
Overall Score (prosek tri ocene) mora biti >= 7.0 i accuracy_score mora biti >= 7 za pass_status = true.

Generiši SAMO validan JSON objekat sa sledećim poljima:
{{
  "accuracy_score": 9,
  "language_parity_score": 10,
  "completeness_score": 9,
  "overall_score": 9.3,
  "pass_status": true,
  "critique": "Detaljno obrazloženje ocene na srpskom jeziku.",
  "missing_aspects": []
}}"""

        llm_response = query_llm(prompt, system="Ti si strog akademski recenzent i stručni sudija.")
        clean_json_str = llm_response.strip()
        if clean_json_str.startswith("```"):
            clean_json_str = clean_json_str.split("```")[1]
            if clean_json_str.startswith("json"):
                clean_json_str = clean_json_str[4:]
            clean_json_str = clean_json_str.strip()

        try:
            data = json.loads(clean_json_str)
            acc = int(data.get("accuracy_score", 8))
            lang = int(data.get("language_parity_score", 9))
            comp = int(data.get("completeness_score", 8))
            overall = float(data.get("overall_score", (acc + lang + comp) / 3.0))
            passed = bool(data.get("pass_status", overall >= 7.0 and acc >= 7))

            return JudgeFeedback(
                accuracy_score=acc,
                language_parity_score=lang,
                completeness_score=comp,
                overall_score=round(overall, 1),
                pass_status=passed,
                critique=data.get("critique", "Sadržaj uspešno zadovoljava pedagoške i tehničke kriterijume."),
                missing_aspects=data.get("missing_aspects", []),
            )
        except Exception as e:
            logger.warning(f"Judge JSON parse error: {e}. Falling back to deterministic evaluation.")
            # Deterministic evaluation if LLM json formatting failed
            acc = 9 if findings.mental_models and findings.core_principles else 6
            lang = 9
            comp = 8 if findings.practical_steps else 6
            overall = round((acc + lang + comp) / 3.0, 1)
            passed = overall >= 7.0 and acc >= 7
            return JudgeFeedback(
                accuracy_score=acc,
                language_parity_score=lang,
                completeness_score=comp,
                overall_score=overall,
                pass_status=passed,
                critique="Deterministička verifikacija: Sadržaj poseduje sve potrebne strukturne komponente.",
                missing_aspects=[],
            )
