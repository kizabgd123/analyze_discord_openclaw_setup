#!/usr/bin/env python3
"""
End-to-End Verification Test for OpenClaw Multi-Agent Engine & NLM Grounding
"""
import asyncio
import json
import logging
from brain_core import BrainCore
from debate_engine import MultiAgentDebateManager, DEFAULT_PERSONAS, DebateTurn
from judge_guard import JudgeGuard

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

async def main():
    print("==================================================")
    print("1. Testing JudgeGuard")
    print("==================================================")
    judge = JudgeGuard()
    verdict = judge.verify("System verification test action")
    print(f"JudgeGuard Verdict: {verdict}")
    assert verdict == "PASSED", f"JudgeGuard failed: {verdict}"

    print("\n==================================================")
    print("2. Testing BrainCore NLM Query")
    print("==================================================")
    brain = BrainCore()
    print(f"BrainCore default_notebook_id: {brain.default_notebook_id}")
    res = await brain._nlm_query(brain.default_notebook_id, "Sta je OpenClaw?")
    print(f"BrainCore NLM Query success: {res.get('success')}")
    if res.get("success"):
        print(f"Answer preview: {res.get('answer')[:120]}...")
    else:
        print(f"Error: {res.get('error')}")

    print("\n==================================================")
    print("3. Testing Debate Engine Personas Configuration")
    print("==================================================")
    engine = MultiAgentDebateManager()
    for p in DEFAULT_PERSONAS:
        p_id = p["id"]
        nb_id = p["default_notebook_id"]
        title = p["notebook_title"]
        print(f"Persona: {p['name']} ({p_id}) -> NB: {nb_id} ({title})")

    print("\n==================================================")
    print("4. Testing Single Turn Generation for Moderator (Švaba)")
    print("==================================================")
    mod = DEFAULT_PERSONAS[0]
    ans, cites = await engine.query_persona_notebook(
        persona=mod,
        topic="OpenClaw 2026 Arhitektura i MCP integracija",
        round_num=1,
        recent_turns=[]
    )
    print(f"Švaba Turn Answer:\n{ans}\nCitations: {cites}")
    assert len(ans) > 0, "Švaba returned empty answer!"

    turn1 = DebateTurn(
        turn_index=0,
        round_number=1,
        persona_id=mod["id"],
        persona_name=mod["name"],
        notebook_id=mod["default_notebook_id"],
        prompt_used="Topic opener",
        response_text=ans,
        citations=cites
    )

    print("\n==================================================")
    print("5. Testing Single Turn Generation for Ekser (Architect)")
    print("==================================================")
    eks = DEFAULT_PERSONAS[1]
    ans_e, cites_e = await engine.query_persona_notebook(
        persona=eks,
        topic="Kako radi Discord bot kao MCP server u 2026?",
        round_num=1,
        recent_turns=[turn1]
    )
    print(f"Ekser Turn Answer:\n{ans_e}\nCitations: {cites_e}")
    assert len(ans_e) > 0, "Ekser returned empty answer!"

    print("\n==================================================")
    print("✅ ALL TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
