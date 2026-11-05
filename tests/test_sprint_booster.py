#!/usr/bin/env python3
"""
tests/test_sprint_booster.py — Unit testovi za SprintBooster i SprintBoosterService.
=====================================================================================
"""

import os
import shutil
from pathlib import Path
import pytest

from sprint_booster import SprintBooster
from src.services.sprint_booster_service import SprintBoosterService


def test_sprint_booster_store_artifact():
    session_id = "test_session_123"
    booster = SprintBooster(session_id=session_id)
    
    agent_name = "AnalystAgent"
    content = "Ovo je super dugačak izveštaj o analizi sistema sa svim detaljima i metrikama." * 50
    
    path = booster.store_artifact(agent_name, content)
    assert path is not None
    assert os.path.exists(path)
    
    saved_text = Path(path).read_text(encoding="utf-8")
    assert saved_text == content
    
    # Clean up
    shutil.rmtree(".cm/sprint/artifacts/test_session_123", ignore_errors=True)


def test_sprint_booster_summarize():
    booster = SprintBooster(session_id="test_session_summary")
    agent_name = "CoderAgent"
    long_output = "A" * 3000
    
    artifact_path = booster.store_artifact(agent_name, long_output)
    summary = booster.summarize_output(agent_name, long_output, artifact_path, max_chars=500)
    
    assert "=== SPRINT BOOSTER COMPRESSED RELAY [CoderAgent] ===" in summary
    assert artifact_path in summary
    assert len(summary) < 1500
    
    shutil.rmtree(".cm/sprint/artifacts/test_session_summary", ignore_errors=True)


def test_sprint_booster_prune_prompt():
    booster = SprintBooster(session_id="test_prune")
    raw_payload = (
        "Zadatak 1\n"
        "Zadatak 1\n"  # duplikat
        "  \n"
        "Detalj iz baze znanja...\n"
        "Detalj iz baze znanja...\n"  # duplikat
    )
    
    pruned = booster.prune_prompt(raw_payload)
    assert "Zadatak 1" in pruned
    assert pruned.count("Zadatak 1") == 1
    assert pruned.count("Detalj iz baze znanja...") == 1


def test_sprint_booster_service_integration():
    service = SprintBoosterService(session_id="test_service_session")
    
    output = "Rezultat rada specijalizovanog agenta za testiranje." * 30
    relay = service.process_agent_output("TestAgent", output)
    
    assert "SPRINT BOOSTER COMPRESSED RELAY" in relay
    assert len(relay) < 1500
    
    optimized_prompt = service.optimize_prompt("  Test prompt payload   \n  Test prompt payload  ")
    assert optimized_prompt.strip() == "Test prompt payload"
    
    shutil.rmtree(".cm/sprint/artifacts/test_service_session", ignore_errors=True)
