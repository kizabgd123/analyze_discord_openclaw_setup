#!/usr/bin/env python3
"""
kaggle_service.py — Verified Kaggle Telemetry Service for OpenClaw.
==================================================================
Strict Zero-Mock / Zero-Simulation policy:
  - Uses official `kaggle` CLI binary via parameterized subprocess (NO shell=True).
  - Validates competition slug with regex ^[a-zA-Z0-9_-]+$.
  - Fetches submissions via `kaggle competitions submissions <comp> --csv`.
  - Fetches submission limits via `kaggle competitions submission-limits <comp> --json`.
  - Computes best score, latest score, and remaining quota dynamically without hardcoding.
  - Fails explicitly on CLI errors without fallback guessing.
"""

import os
import re
import csv
import json
import shutil
import asyncio
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

logger = logging.getLogger("KaggleService")

KAGGLE_BIN = shutil.which("kaggle") or "/home/kizamladjanijebac/.local/bin/kaggle"
SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


class KaggleCLIError(Exception):
    """Raised when Kaggle CLI command execution fails."""
    pass


@dataclass
class KaggleSubmission:
    ref: str
    file_name: str
    date: str
    description: str
    status: str
    public_score: Optional[float]
    private_score: Optional[float]


@dataclass
class KaggleSubmissionLimits:
    total: int
    remaining_today: int


@dataclass
class KaggleCompetitionContext:
    competition: str
    total_submissions: int
    best_score: Optional[float]
    best_date: Optional[str]
    latest_score: Optional[float]
    latest_date: Optional[str]
    remaining_today: int
    submissions: List[KaggleSubmission]
    summary_markdown: str


class KaggleService:
    """Provides validated Kaggle competition telemetry via Kaggle CLI."""

    def __init__(self, kaggle_bin: str = KAGGLE_BIN):
        self.kaggle_bin = kaggle_bin

    def validate_slug(self, slug: str) -> str:
        """Validates competition slug format to prevent command injection."""
        if not slug or not SLUG_PATTERN.match(slug.strip()):
            raise ValueError(
                f"Invalid competition slug: '{slug}'. Must match pattern ^[a-zA-Z0-9_-]+$"
            )
        return slug.strip()

    def parse_submissions_csv(self, raw_csv: str) -> List[KaggleSubmission]:
        """Parses CSV output from `kaggle competitions submissions <comp> --csv`."""
        lines = []
        for line in raw_csv.splitlines():
            # Strip CLI update warnings or diagnostic notices
            if line.startswith("Warning:") or line.startswith("🔔"):
                continue
            if line.strip():
                lines.append(line)

        if not lines:
            return []

        reader = csv.DictReader(lines)
        submissions: List[KaggleSubmission] = []
        for row in reader:
            raw_pub = row.get("publicScore", "")
            raw_priv = row.get("privateScore", "")

            pub_score = None
            if raw_pub and raw_pub.strip():
                try:
                    pub_score = float(raw_pub.strip())
                except ValueError:
                    pub_score = None

            priv_score = None
            if raw_priv and raw_priv.strip():
                try:
                    priv_score = float(raw_priv.strip())
                except ValueError:
                    priv_score = None

            submissions.append(
                KaggleSubmission(
                    ref=row.get("ref", "").strip(),
                    file_name=row.get("fileName", "").strip(),
                    date=row.get("date", "").strip(),
                    description=row.get("description", "").strip(),
                    status=row.get("status", "").strip(),
                    public_score=pub_score,
                    private_score=priv_score,
                )
            )
        return submissions

    def parse_limits_json(self, raw_json: str) -> KaggleSubmissionLimits:
        """Parses JSON output from `kaggle competitions submission-limits <comp> --json`."""
        # Locate JSON block in output
        match = re.search(r"\{.*\}", raw_json, re.DOTALL)
        if not match:
            raise KaggleCLIError(f"Could not parse JSON from submission-limits: {raw_json}")

        try:
            data = json.loads(match.group(0))
            return KaggleSubmissionLimits(
                total=int(data.get("numTotal", 0)),
                remaining_today=int(data.get("numAllowedNow", 0)),
            )
        except Exception as e:
            raise KaggleCLIError(f"Failed to decode submission-limits JSON: {e}")

    def build_context_from_data(
        self,
        competition: str,
        submissions: List[KaggleSubmission],
        limits: KaggleSubmissionLimits,
    ) -> KaggleCompetitionContext:
        """Constructs KaggleCompetitionContext from parsed telemetry."""
        total = len(submissions)
        valid_scores = [(s.public_score, s.date) for s in submissions if s.public_score is not None]

        best_score = None
        best_date = None
        latest_score = None
        latest_date = None

        if valid_scores:
            # Submissions are listed most recent first
            latest_score, latest_date = valid_scores[0]
            # Best score is maximum public score
            best_tuple = max(valid_scores, key=lambda x: x[0])
            best_score, best_date = best_tuple

        summary_lines = [
            f"### Kaggle Telemetry: `{competition}`",
            f"- **Ukupno podnetih rešenja:** {total}",
            f"- **Preostalo submisija danas:** {limits.remaining_today}",
        ]
        if best_score is not None:
            summary_lines.append(f"- **Najbolji istorijski skor (LB):** `{best_score}` (datum: {best_date})")
            summary_lines.append(f"- **Poslednji skor (LB):** `{latest_score}` (datum: {latest_date})")
        else:
            summary_lines.append("- **Status istorije:** No previous submissions found on leaderboard.")

        return KaggleCompetitionContext(
            competition=competition,
            total_submissions=total,
            best_score=best_score,
            best_date=best_date,
            latest_score=latest_score,
            latest_date=latest_date,
            remaining_today=limits.remaining_today,
            submissions=submissions,
            summary_markdown="\n".join(summary_lines),
        )

    async def get_competition_submissions(
        self, competition: str, timeout: float = 30.0
    ) -> List[KaggleSubmission]:
        """Calls `kaggle competitions submissions <competition> --csv`."""
        comp = self.validate_slug(competition)
        cmd = [self.kaggle_bin, "competitions", "submissions", comp, "--csv"]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            out_str = stdout.decode("utf-8", errors="replace").strip()
            err_str = stderr.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                raise KaggleCLIError(
                    f"Kaggle submissions command failed (exit code {proc.returncode}): {err_str or out_str}"
                )

            return self.parse_submissions_csv(out_str)

        except asyncio.TimeoutError:
            raise KaggleCLIError(f"Kaggle submissions timed out after {timeout}s for {comp}")
        except FileNotFoundError:
            raise KaggleCLIError(f"Kaggle binary not found at {self.kaggle_bin}")

    async def get_submission_limits(
        self, competition: str, timeout: float = 30.0
    ) -> KaggleSubmissionLimits:
        """Calls `kaggle competitions submission-limits <competition> --json`."""
        comp = self.validate_slug(competition)
        cmd = [self.kaggle_bin, "competitions", "submission-limits", comp, "--json"]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            out_str = stdout.decode("utf-8", errors="replace").strip()
            err_str = stderr.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                raise KaggleCLIError(
                    f"Kaggle submission-limits command failed (exit code {proc.returncode}): {err_str or out_str}"
                )

            return self.parse_limits_json(out_str)

        except asyncio.TimeoutError:
            raise KaggleCLIError(f"Kaggle submission-limits timed out after {timeout}s for {comp}")
        except FileNotFoundError:
            raise KaggleCLIError(f"Kaggle binary not found at {self.kaggle_bin}")

    async def get_competition_context(
        self, competition: str, timeout: float = 60.0
    ) -> KaggleCompetitionContext:
        """Fetches submissions and limits concurrently, returning unified telemetry."""
        comp = self.validate_slug(competition)
        submissions, limits = await asyncio.gather(
            self.get_competition_submissions(comp, timeout=timeout / 2),
            self.get_submission_limits(comp, timeout=timeout / 2),
        )
        return self.build_context_from_data(comp, submissions, limits)


# Singleton
kaggle_service = KaggleService()
