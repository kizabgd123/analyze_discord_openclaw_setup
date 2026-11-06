"""
submission_service.py — Deterministic Kaggle Submission Management.
===================================================================
Enforces strict competition submission constraints:
  - Hard limit of 5 submissions per run.
  - Tag template: s6e11-<run_id>-<exp_no>.
  - Pre-submission validation: remaining count check, SHA-256 computation.
  - Interactive confirmation on first submission.
  - Post-submission verification: filters strictly by tag, never reads older submissions.
"""

import os
import hashlib
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger("Kaggle2.SubmissionService")

COMPETITION_ID = "playground-series-s6e11"


class SubmissionService:
    """Manages Kaggle submissions with hard cap and tag isolation."""

    def __init__(self, run_id: str, max_submissions_per_run: int = 5):
        self.run_id = run_id
        self.max_submissions = max_submissions_per_run
        self.submitted_count = 0
        self.best_cv_score: float = -1.0
        self.submissions_log: List[Dict[str, Any]] = []

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    async def get_remaining_kaggle_submissions(self) -> Dict[str, Any]:
        """Queries the official Kaggle API for today's submission limits."""
        import kaggle
        try:
            api = kaggle.api
            api.authenticate()
            limits = api.competition_get_submission_limits(COMPETITION_ID)
            # Format: {"numToday": X, "numTotal": Y, "numAllowedNow": Z, ...}
            remaining_today = limits.get("numAllowedNow", 0)
            return {
                "status": "PASSED",
                "remaining_today": remaining_today,
                "num_today": limits.get("numToday", 0),
                "num_total": limits.get("numTotal", 10)
            }
        except Exception as exc:
            logger.error(f"Error fetching Kaggle limits: {exc}")
            return {
                "status": "FAILED",
                "remaining_today": 0,
                "error": str(exc)
            }

    async def prepare_submission(self, exp_no: int, submission_file: Path, cv_score: float, is_experiment: bool = False) -> Dict[str, Any]:
        """
        Validates whether submission is allowed and prepares command and metadata.
        """
        submission_file = Path(submission_file)
        if not submission_file.is_file():
            return {"status": "BLOCKED", "reason": f"File not found: {submission_file}"}

        if self.submitted_count >= self.max_submissions:
            return {"status": "BLOCKED", "reason": f"Run submission budget reached ({self.submitted_count}/{self.max_submissions})"}

        # CV improvement check
        if not is_experiment and cv_score <= self.best_cv_score:
            return {
                "status": "BLOCKED",
                "reason": f"CV score {cv_score:.5f} does not beat best score so far ({self.best_cv_score:.5f})"
            }

        limits = await self.get_remaining_kaggle_submissions()
        if limits.get("remaining_today", 0) <= 0:
            return {
                "status": "BLOCKED",
                "reason": f"Kaggle daily limit reached ({limits.get('num_today', 0)}/{limits.get('num_total', 10)})"
            }

        tag = f"s6e11-{self.run_id}-{exp_no}"
        sha256 = self.compute_sha256(submission_file)
        cmd_str = f"kaggle competitions submit -c {COMPETITION_ID} -f {submission_file.name} -m '{tag}'"

        return {
            "status": "READY",
            "tag": tag,
            "file_path": str(submission_file.resolve()),
            "file_name": submission_file.name,
            "sha256": sha256,
            "command": cmd_str,
            "cv_score": cv_score,
            "remaining_budget": self.max_submissions - self.submitted_count,
            "kaggle_remaining_today": limits.get("remaining_today", 0),
            "is_first_submission": (self.submitted_count == 0)
        }

    async def execute_submission(self, exp_no: int, submission_file: Path, cv_score: float, is_experiment: bool = False) -> Dict[str, Any]:
        """
        Executes actual submission to Kaggle via the CLI.
        """
        prep = await self.prepare_submission(exp_no, submission_file, cv_score, is_experiment)
        if prep.get("status") != "READY":
            return prep

        tag = prep["tag"]
        cmd = ["kaggle", "competitions", "submit", "-c", COMPETITION_ID, "-f", str(submission_file.resolve()), "-m", tag]
        logger.info(f"[SubmissionService] Executing submit: {cmd}")

        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        raw_stdout = stdout.decode().strip()
        raw_stderr = stderr.decode().strip()

        if proc.returncode != 0:
            err = raw_stderr or raw_stdout or f"Submit exited with {proc.returncode}"
            logger.error(f"[SubmissionService] Submission failed: {err}")
            return {"status": "FAILED", "error": err, "tag": tag}

        self.submitted_count += 1
        if cv_score > self.best_cv_score:
            self.best_cv_score = cv_score

        # Poll Kaggle to verify submission row
        await asyncio.sleep(5)
        public_score = await self.poll_submission_public_score(tag)

        record = {
            "exp_no": exp_no,
            "tag": tag,
            "file_name": submission_file.name,
            "sha256": prep["sha256"],
            "cv_score": cv_score,
            "public_score": public_score,
            "status": "SUBMITTED",
            "submitted_count": self.submitted_count,
            "remaining_budget": self.max_submissions - self.submitted_count
        }
        self.submissions_log.append(record)
        return {"status": "PASSED", "record": record}

    async def poll_submission_public_score(self, tag: str, retries: int = 6, delay: int = 5) -> Optional[float]:
        """Polls Kaggle submissions table and parses public score for our tag."""
        import kaggle
        api = kaggle.api
        api.authenticate()

        for _ in range(retries):
            try:
                subs = api.competition_submissions(COMPETITION_ID)
                sub_list = subs.submissions if hasattr(subs, "submissions") else list(subs)
                for s in sub_list:
                    desc = getattr(s, "description", "")
                    if desc == tag:
                        score_str = getattr(s, "publicScore", getattr(s, "public_score", None))
                        if score_str not in [None, "", "None"]:
                            try:
                                return float(score_str)
                            except ValueError:
                                pass
            except Exception as e:
                logger.warning(f"Error checking submission score: {e}")
            await asyncio.sleep(delay)
        return None

    async def list_run_submissions(self) -> List[Dict[str, Any]]:
        """Queries Kaggle submissions and filters STRICTLY by our run tag prefix."""
        import kaggle
        api = kaggle.api
        api.authenticate()
        filtered: List[Dict[str, Any]] = []

        try:
            subs = api.competition_submissions(COMPETITION_ID)
            sub_list = subs.submissions if hasattr(subs, "submissions") else list(subs)
            run_prefix = f"s6e11-{self.run_id}-"
            for s in sub_list:
                desc = getattr(s, "description", "")
                if desc.startswith(run_prefix):
                    filtered.append({
                        "ref": getattr(s, "ref", ""),
                        "file_name": getattr(s, "fileName", getattr(s, "file_name", "")),
                        "date": str(getattr(s, "date", "")),
                        "description": desc,
                        "status": str(getattr(s, "status", "")),
                        "public_score": getattr(s, "publicScore", getattr(s, "public_score", None))
                    })
        except Exception as exc:
            logger.error(f"Error listing filtered submissions: {exc}")
        return filtered
