"""Live Evidence Runner (Zero-Mock Verification).
Executes each agent step in the A2A pipeline live and prints the unedited raw output.
"""

import sys
import os
import json
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from a2tools_runtime import tools_runtime
from a2a_lms.shared.schemas import ResearchFindings, JudgeFeedback, YouTubeMetadata
from a2a_lms.shared.youtube_lookup import find_embeddable_youtube_video
from a2a_lms.agents.researcher.agent import PrincipalResearcherAgent
from a2a_lms.agents.judge.agent import SeniorJudgeAgent
from a2a_lms.agents.content_builder.agent import LeadContentBuilderAgent
from a2a_lms.agents.orchestrator.agent import LMSOrchestrator


async def main():
    topic = "Google ADK A2A Multi-Agent Sistemi 2026"
    notebook_id = "9c8878e1-1fb4-4035-b022-7678a10be7f3"

    print("=" * 80)
    print("DOKAZ 1: DIREKTAN UPIT KA NOTEBOOKLM BAZI (9c8878e1-1fb4-4035-b022-7678a10be7f3)")
    print("=" * 80)
    nlm_query = (
        "Objasni detaljno 7 interaktivnih celina masterclass kursa, ulogu Senior Judge agenta "
        "i eliminaciju veštačkih slajdova u Google ADK LMS sistemu 2026."
    )
    print(f"Postavljeno pitanje svesci:\n{nlm_query}\n")
    nlm_res = await tools_runtime.query_notebooklm(notebook_id, nlm_query)
    print(f"Status odgovora: {nlm_res.success}")
    print(f"Greška (ako postoji): {nlm_res.error_type}")
    print("\nSIROVI ODGOVOR IZ NOTEBOOKLM SVESKE:")
    print("-" * 60)
    print(nlm_res.output)
    print("-" * 60)

    print("\n" + "=" * 80)
    print("DOKAZ 2: PRINCIPAL RESEARCHER AGENT — ISTRAŽIVANJE I IZDVAJANJE TEMELJA")
    print("=" * 80)
    researcher = PrincipalResearcherAgent(notebook_id=notebook_id)
    findings = await researcher.research(topic)
    print(f"Domen: {findings.domain_type}")
    print(f"Mentalni modeli: {json.dumps(findings.mental_models, ensure_ascii=False, indent=2)}")
    print(f"Temeljni principi: {json.dumps(findings.core_principles, ensure_ascii=False, indent=2)}")
    print(f"Praktični koraci: {json.dumps(findings.practical_steps, ensure_ascii=False, indent=2)}")
    print(f"Zamke i zablude: {json.dumps(findings.traps_and_pitfalls, ensure_ascii=False, indent=2)}")

    print("\n" + "=" * 80)
    print("DOKAZ 3: SENIOR JUDGE AGENT — EVALUACIJA I RUBRIKA OCENJIVANJA")
    print("=" * 80)
    judge = SeniorJudgeAgent()
    judge_feedback = judge.evaluate(findings)
    print(f"Tačnost (Accuracy): {judge_feedback.accuracy_score}/10")
    print(f"Jezički kontinuitet (Srpski): {judge_feedback.language_parity_score}/10")
    print(f"Kompletnost i domen: {judge_feedback.completeness_score}/10")
    print(f"Ukupna ocena (Overall): {judge_feedback.overall_score}/10")
    print(f"Status prolaza (Pass): {judge_feedback.pass_status}")
    print(f"Kritika i obrazloženje:\n{judge_feedback.critique}")

    print("\n" + "=" * 80)
    print("DOKAZ 4: AUTENTIČNI YOUTUBE DISCOVERY & oEmbed VALIDACIJA")
    print("=" * 80)
    yt_meta = find_embeddable_youtube_video(topic, domain_type=findings.domain_type)
    print(f"Video ID: {yt_meta.video_id}")
    print(f"Naslov: {yt_meta.title}")
    print(f"Autor: {yt_meta.author}")
    print(f"Trajanje: {yt_meta.duration_formatted} ({yt_meta.duration_seconds}s)")
    print(f"Nocookie Embed URL: {yt_meta.embed_url}")
    print(f"oEmbed Verifikovano: {yt_meta.verified}")
    print("Poglavlja sa vremenskim oznakama:")
    for ch in yt_meta.chapters:
        print(f"  [{ch.timestamp}] ({ch.seconds}s) -> {ch.title}")

    print("\n" + "=" * 80)
    print("DOKAZ 5: LEAD CONTENT BUILDER AGENT — GENERISANJE 7 CELINA KURSA")
    print("=" * 80)
    builder = LeadContentBuilderAgent()
    course = builder.build_course(findings, judge_feedback, yt_meta)
    print(f"Verifikacioni Hash: {course.verification_hash}")
    print(f"Broj sekcija: {len(course.sections)}")
    print(f"Broj 3D fleš-kartica: {len(course.flashcards)}")
    print(f"Broj kviz pitanja: {len(course.quiz)}")

    # Save to disk
    out_dir = Path(__file__).resolve().parent.parent / "generated_courses"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "adk_masterclass_live.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(course.full_course_markdown)
    print(f"\nCeo kurs sačuvan na: {out_file} (Veličina: {len(course.full_course_markdown)} karaktera)")

    print("\n" + "=" * 80)
    print("DOKAZ 6: ISPIS GENERISANIH MODULA (KOMPLETAN SADRŽAJ)")
    print("=" * 80)
    for s in course.sections:
        print(f"\n--- [SEKCIJA {s.index}: {s.title}] ---")
        print(s.content_markdown[:600] + ("\n... [nastavak u fajlu]" if len(s.content_markdown) > 600 else ""))

    print("\n--- [3D FLEŠ-KARTICE] ---")
    for i, fc in enumerate(course.flashcards, 1):
        print(f"Kartica {i}: P: {fc.front} | O: {fc.back}")

    print("\n--- [INTERAKTIVNI KVIZ ZNANJA] ---")
    for i, q in enumerate(course.quiz, 1):
        print(f"\nPitanje {i}: {q.question}")
        for j, opt in enumerate(q.options):
            marker = "[x]" if j == q.correct_index else "[ ]"
            print(f"  {marker} {chr(65+j)}) {opt}")
        print(f"  Objašnjenje: {q.explanation}")


if __name__ == "__main__":
    asyncio.run(main())
