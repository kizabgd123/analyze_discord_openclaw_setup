"""Live Evidence Runner (Zero-Mock Verification with Autonomous Agents Hardening).
Executes each agent step in the A2A pipeline live and prints the unedited raw output,
including ReAct reasoning traces, durable checkpoints, and cost guard metrics.
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
from a2a_lms.shared.cost_guard import CostAndStepGuard
from a2a_lms.shared.checkpoint import LMSCheckpointManager
from a2a_lms.agents.orchestrator.agent import LMSOrchestrator


async def main():
    topic = sys.argv[1] if len(sys.argv) > 1 else "poker texas holdem"

    print("=" * 80)
    print(f"POKRETANJE AUTONOMNOG A2A PIPELINE-A ZA TEMU: '{topic}'")
    print("=" * 80)

    orchestrator = LMSOrchestrator()
    thread_id = orchestrator.checkpoint_manager.create_thread_id("live-run")
    print(f"Dodeljen Durable Thread ID: {thread_id}")

    course = await orchestrator.run(
        topic=topic,
        thread_id=thread_id,
        on_progress=lambda msg: print(f"  [STREAM PROGRESS] {msg}"),
    )

    print("\n" + "=" * 80)
    print("DOKAZ 1: AUTENTIČNI YOUTUBE VIDEO I USKLAĐENA POGLAVLJA")
    print("=" * 80)
    yt = course.youtube_metadata
    print(f"Video ID:        {yt.video_id}")
    print(f"Naslov:          {yt.title}")
    print(f"Kanal / Autor:   {yt.author}")
    print(f"oEmbed Potvrda:  {yt.verified}")
    print(f"Embed URL:       {yt.embed_url}")
    print("Poglavlja (Sinhronizovana sa temom):")
    for ch in yt.chapters:
        print(f"  [{ch.timestamp}] {ch.title}")

    print("\n" + "=" * 80)
    print("DOKAZ 2: SENIOR JUDGE AUDIT & DOMENSKA EVALUACIJA")
    print("=" * 80)
    jf = course.judge_feedback
    print(f"Tačnost (Accuracy):                    {jf.accuracy_score}/10")
    print(f"Jezički kontinuitet (Srpski):          {jf.language_parity_score}/10")
    print(f"Kompletnost i domen:                  {jf.completeness_score}/10")
    print(f"Ukupna ocena (Overall):                {jf.overall_score}/10")
    print(f"Status prolaza (Pass):                 {jf.pass_status}")
    print(f"Uzemljenost potvrđena (Grounding):     {jf.grounding_verified}")
    print(f"Kritika i obrazloženje:\n{jf.critique}")

    print("\n" + "=" * 80)
    print("DOKAZ 3: ReAct TRAGOVI RADA (THOUGHT -> ACTION -> OBSERVATION -> REFLECTION)")
    print("=" * 80)
    for step in course.trace_history:
        print(f"\n[KORAK {step.step_number}] Agent: {step.agent_name} ({step.tokens_used} tokena)")
        print(f"  💭 Thought:     {step.thought}")
        print(f"  ⚡ Action:      {step.action}")
        print(f"  👁️ Observation: {step.observation}")
        if step.reflection:
            print(f"  ⚖️ Reflection:  {step.reflection}")

    print("\n" + "=" * 80)
    print("DOKAZ 4: METRIKE TROŠKOVA, BROJA KORAKA I CHECKPOINT STANJA")
    print("=" * 80)
    m = course.execution_metrics
    if m:
        print(f"Ukupno koraka (Total Steps):           {m.total_steps}")
        print(f"Ukupno tokena (Estimated Tokens):      {m.total_estimated_tokens}")
        print(f"Procenjeni trošak (Cost USD):          ${m.estimated_cost_usd:.5f}")
        print(f"Trajanje izvršenja (Seconds):          {m.execution_time_seconds}s")
        print(f"Durable Checkpoint ID:                 {m.checkpoint_id}")
        print(f"Uzemljenost (Grounding Confidence):    {round(m.grounding_confidence * 100)}%")

    # Verify checkpoint on disk
    saved_ckpt = orchestrator.checkpoint_manager.load_checkpoint(thread_id)
    print(f"Checkpoint na disku postoji:           {saved_ckpt is not None}")
    if saved_ckpt:
        print(f"Faza sačuvana u checkpoint-u:          {saved_ckpt.get('current_stage')}")

    print("\n" + "=" * 80)
    print("DOKAZ 5: INTERAKTIVNI MODULI I 7 CELINA MASTERCLASS KURSA")
    print("=" * 80)
    print(f"Broj modula kursa:       {len(course.sections)}")
    for s in course.sections:
        print(f"  - Sekcija {s.index}: {s.title} ({len(s.content_markdown)} karaktera)")
    print(f"Broj 3D fleš-kartica:    {len(course.flashcards)}")
    for idx, fc in enumerate(course.flashcards, 1):
        print(f"  * Kartica {idx}: {fc.front} ➔ {fc.back}")
    print(f"Broj kviz pitanja:       {len(course.quiz)}")
    for idx, q in enumerate(course.quiz, 1):
        print(f"  * Pitanje {idx}: {q.question}")
    print(f"Verifikacioni Hash:      {course.verification_hash}")

    # Save to disk
    out_dir = Path(__file__).resolve().parent.parent / "generated_courses"
    out_dir.mkdir(exist_ok=True)
    slug = "".join(c if c.isalnum() else "_" for c in topic.lower()).strip("_")
    out_file = out_dir / f"{slug}_masterclass_live.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(course.full_course_markdown)
    print(f"\nCeo kurs sačuvan na: {out_file} (Veličina: {len(course.full_course_markdown)} karaktera)")


if __name__ == "__main__":
    asyncio.run(main())
