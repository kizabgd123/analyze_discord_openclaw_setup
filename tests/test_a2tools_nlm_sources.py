import pytest
from a2tools_runtime import tools_runtime, ORCHESTRATION_NOTEBOOK_ID


@pytest.mark.asyncio
async def test_list_notebook_sources_returns_valid_list():
    sources = await tools_runtime.list_notebook_sources(ORCHESTRATION_NOTEBOOK_ID)
    assert isinstance(sources, list)
    assert len(sources) >= 14
    first = sources[0]
    assert "id" in first
    assert "title" in first


@pytest.mark.asyncio
async def test_filter_sources_by_competition():
    from src.services.kaggle_debate_service import filter_competition_sources

    sources = await tools_runtime.list_notebook_sources(ORCHESTRATION_NOTEBOOK_ID)

    ntl_sources = filter_competition_sources(sources, "name-that-llm")
    assert len(ntl_sources) >= 10
    for s in ntl_sources:
        assert "gemma" not in s["title"].lower()

    gemma_sources = filter_competition_sources(sources, "gemma-4-developer-agent")
    assert len(gemma_sources) >= 1
    for s in gemma_sources:
        assert "gemma" in s["title"].lower()
