import re
import csv
import subprocess
import pytest
from pathlib import Path

# Step 1: imports from src.services.kaggle_service
from src.services.kaggle_service import (
    KaggleService,
    KaggleSubmission,
    KaggleSubmissionLimits,
    KaggleCompetitionContext,
    KaggleCLIError,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.mark.asyncio
async def test_slug_validation_rejects_malicious_input():
    service = KaggleService()
    invalid_slugs = [
        "name-that-llm; rm -rf /",
        "comp | ls",
        "comp`whoami`",
        "comp $(id)",
        "comp with spaces",
        "comp/../../etc/passwd",
    ]
    for slug in invalid_slugs:
        with pytest.raises(ValueError, match="Invalid competition slug"):
            await service.get_competition_context(slug)


def test_parser_unit_on_stored_real_fixture():
    fixture_path = FIXTURES_DIR / "name_that_llm_submissions.csv"
    assert fixture_path.exists(), f"Missing fixture at {fixture_path}"
    raw_csv = fixture_path.read_text(encoding="utf-8")

    service = KaggleService()
    submissions = service.parse_submissions_csv(raw_csv)

    assert len(submissions) >= 12
    # Verify exact parsed properties on real fixture
    scores = [s.public_score for s in submissions if s.public_score is not None]
    assert len(scores) >= 12
    assert max(scores) == 0.604
    assert submissions[0].public_score == 0.348


def test_parser_unit_on_empty_submissions():
    empty_csv = "Warning: outdated version\nref,fileName,date,description,status,publicScore,privateScore\n"
    service = KaggleService()
    submissions = service.parse_submissions_csv(empty_csv)
    assert submissions == []

    context = service.build_context_from_data(
        competition="empty-comp",
        submissions=[],
        limits=KaggleSubmissionLimits(total=0, remaining_today=5),
    )
    assert context.total_submissions == 0
    assert context.best_score is None
    assert context.latest_score is None
    assert context.best_date is None
    assert context.latest_date is None
    assert context.remaining_today == 5
    assert "No previous submissions found" in context.summary_markdown


@pytest.mark.asyncio
async def test_cli_error_raises_explicit_exception():
    service = KaggleService()
    # A competition that does not exist must raise KaggleCLIError, never default to 0.0
    with pytest.raises(KaggleCLIError) as exc_info:
        await service.get_competition_context("nonexistent-competition-xyz-987654321")
    assert "failed" in str(exc_info.value).lower() or "404" in str(exc_info.value) or "error" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_live_cli_execution_matches_independent_parse():
    service = KaggleService()
    ctx = await service.get_competition_context("name-that-llm")

    # Run independent external verification via standard subprocess to verify zero hardcoding
    res = subprocess.run(
        ["kaggle", "competitions", "submissions", "name-that-llm", "--csv"],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [line for line in res.stdout.splitlines() if not line.startswith("Warning:")]
    reader = csv.DictReader(lines)
    independent_rows = list(reader)

    valid_scores = []
    for r in independent_rows:
        val = r.get("publicScore")
        if val and val.strip():
            try:
                valid_scores.append(float(val.strip()))
            except ValueError:
                pass

    independent_best = max(valid_scores) if valid_scores else None
    independent_latest = valid_scores[0] if valid_scores else None

    # Assert dynamic agreement without hardcoding numbers
    assert ctx.total_submissions == len(independent_rows)
    assert ctx.best_score == independent_best
    assert ctx.latest_score == independent_latest
    assert ctx.remaining_today >= 0
    assert str(independent_best) in ctx.summary_markdown
