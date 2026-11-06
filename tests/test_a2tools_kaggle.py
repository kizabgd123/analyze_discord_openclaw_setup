import pytest
from a2tools_runtime import tools_runtime


@pytest.mark.asyncio
async def test_tools_runtime_rejects_malicious_slug():
    res = await tools_runtime.get_kaggle_context("comp; rm -rf /")
    assert res.success is False
    assert res.is_error is True
    assert res.error_type == "validation_error"


@pytest.mark.asyncio
async def test_tools_runtime_handles_nonexistent_comp():
    res = await tools_runtime.get_kaggle_context("nonexistent-comp-123456789")
    assert res.success is False
    assert res.is_error is True
    assert res.error_type == "kaggle_cli_error"


@pytest.mark.asyncio
async def test_tools_runtime_fetches_real_kaggle_context():
    res = await tools_runtime.get_kaggle_context("name-that-llm")
    assert res.success is True
    assert res.is_error is False
    assert "metadata" in res.to_dict()
    assert res.metadata["competition"] == "name-that-llm"
    assert res.metadata["total_submissions"] >= 12
    assert res.metadata["remaining_today"] >= 0
    assert res.metadata["best_score"] is not None
    assert res.metadata["latest_score"] is not None
    assert str(res.metadata["best_score"]) in res.output
