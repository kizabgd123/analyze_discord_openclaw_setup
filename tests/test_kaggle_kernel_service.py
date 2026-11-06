import json
import pytest
from pathlib import Path
from src.services.kaggle_kernel_service import (
    KaggleKernelService,
    generate_kernel_metadata,
)


def test_generate_kernel_metadata_strict_allowlist():
    meta = generate_kernel_metadata(
        competition="name-that-llm",
        kernel_slug="ntl-test-validation",
        code_file="pipeline.py",
        gpu_type="NvidiaTeslaT4",
    )
    assert meta["enable_internet"] is False
    assert meta["enable_gpu"] is True
    assert meta["machine_shape"] == "NvidiaTeslaT4"
    assert meta["competition_sources"] == ["name-that-llm"]
    assert "bbucxi/qwen35-9b-safetensors" in meta["dataset_sources"]
    assert "qwen-lm/qwen-3/Transformers/14b-base/1" in meta["model_sources"]


def test_generate_kernel_metadata_rejects_invalid_gpu():
    with pytest.raises(ValueError, match="Invalid GPU type"):
        generate_kernel_metadata(
            competition="name-that-llm",
            kernel_slug="ntl-test-validation",
            gpu_type="InvalidH100Extreme",
        )


@pytest.mark.asyncio
async def test_get_quota_live_execution():
    service = KaggleKernelService()
    quota = await service.get_quota()

    assert "GPU" in quota
    assert quota["GPU"]["total"] == 30.0
    assert quota["GPU"]["remaining"] > 0
    assert quota["GPU"]["used"] >= 0


def test_sanitize_submit_message():
    service = KaggleKernelService()
    raw = "My test; rm -rf / | $(id)"
    sanitized = service.sanitize_message(raw)
    assert ";" not in sanitized
    assert "|" not in sanitized
    assert "$" not in sanitized
    assert "rm" in sanitized
    assert len(sanitized) <= 60
