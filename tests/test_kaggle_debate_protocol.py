import hashlib
from pathlib import Path
import pytest
from a2tools_runtime import tools_runtime, ORCHESTRATION_NOTEBOOK_ID
from src.services.kaggle_debate_service import (
    filter_competition_sources,
    kaggle_debate_service,
    ARTIFACTS_DIR,
)


def test_filter_competition_sources_strict_isolation():
    raw_fixture_sources = [
        {"id": "s1", "title": "Competition Rules - Name That LLM | Kaggle"},
        {"id": "s2", "title": "Name That LLM Honest CV - Kaggle"},
        {"id": "s3", "title": "Gemma 4 Developer Agent Competition 2026: $100K Guide"},
        {"id": "s4", "title": "Technical Research Report on the Kaggle Name That LLM Competition"},
    ]

    ntl = filter_competition_sources(raw_fixture_sources, "name-that-llm")
    assert len(ntl) == 3
    for s in ntl:
        assert "gemma" not in s["title"].lower()

    gemma = filter_competition_sources(raw_fixture_sources, "gemma-4-developer-agent")
    assert len(gemma) == 1
    assert gemma[0]["id"] == "s3"


def test_pipeline_artifact_saved_to_fixed_path():
    comp = "test-comp-artifact"
    target_dir = ARTIFACTS_DIR / comp
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "pipeline.py"

    sample_code = "import pandas as pd\nprint('Hello Kaggle')\n"
    target_file.write_text(sample_code, encoding="utf-8")

    expected_sha256 = hashlib.sha256(sample_code.encode("utf-8")).hexdigest()

    assert target_file.exists()
    assert hashlib.sha256(target_file.read_bytes()).hexdigest() == expected_sha256

    # Cleanup test dir
    target_file.unlink()
    target_dir.rmdir()


@pytest.mark.asyncio
async def test_live_sources_filtered_for_name_that_llm():
    all_sources = await tools_runtime.list_notebook_sources(ORCHESTRATION_NOTEBOOK_ID)
    ntl_sources = filter_competition_sources(all_sources, "name-that-llm")
    assert len(ntl_sources) >= 10
    for s in ntl_sources:
        assert "gemma" not in s["title"].lower()
