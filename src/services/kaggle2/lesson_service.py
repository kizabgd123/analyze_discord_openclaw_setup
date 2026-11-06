"""
lesson_service.py — Structured Lesson Generation & NotebookLM Ingestion.
========================================================================
After every experiment, produces a structured postmortem lesson markdown,
saves it to artifacts/kaggle/s6e11/<run_id>/lessons/, and ingests it back
into the NotebookLM notebook as a new source for future experiment planning.
Header is strictly code-generated from harness outputs (no free-text claims).
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("Kaggle2.LessonService")


class LessonService:
    """Manages the creation, persistence, and NotebookLM ingestion of experiment lessons."""

    def __init__(self, run_dir: Path, notebook_client: Optional[Any] = None):
        self.run_dir = Path(run_dir)
        self.lessons_dir = self.run_dir / "lessons"
        self.lessons_dir.mkdir(parents=True, exist_ok=True)
        self.notebook_client = notebook_client

    async def create_lesson(
        self,
        exp_no: int,
        hypothesis: str,
        methodology: str,
        cv_score: Optional[float],
        what_worked: str,
        what_failed: str,
        why_reasoning: str,
        next_steps: str,
        run_id: str = "UNKNOWN_RUN",
        status: str = "PASSED",
        fold_scores: Optional[Dict[str, float]] = None,
        base_cv_score: Optional[float] = None,
        base_fold_scores: Optional[Dict[str, float]] = None,
        verdict_info: Optional[Dict[str, Any]] = None,
        script_sha256: Optional[str] = None,
        oof_sha256: Optional[str] = None,
        submission_sha256: Optional[str] = None,
        git_commit: Optional[str] = None,
        wall_time: Optional[float] = None,
        exit_code: Optional[int] = 0,
        signal: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Creates a structured lesson with a code-generated header from harness outputs,
        writes it to disk, and ingests it into NotebookLM.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        score_display = f"{cv_score:.5f}" if cv_score is not None else "NONE"

        # Code-generated verdict string vs Exp 0 baseline
        verdict_str = "UNVERIFIED"
        diff_str = "N/A"
        if verdict_info:
            verdict_str = verdict_info.get("verdict", "SAME")
            diff_str = f"{verdict_info.get('mean_diff', 0.0):+.5f} (paired: {verdict_info.get('paired_diffs', [])})"

        # Format fold scores
        folds_str = "None"
        if fold_scores:
            folds_str = ", ".join(f"F{k}: {v:.5f}" for k, v in sorted(fold_scores.items()))

        content = f"""# Lesson: Run {run_id} — Experiment {exp_no}
- **Status:** {status}
- **Verdict vs Baseline (Exp 0):** {verdict_str} [Mean Diff: {diff_str}]
- **Overall CV ROC-AUC:** {score_display}
- **Per-Fold CV ROC-AUC:** [{folds_str}]
- **Baseline CV ROC-AUC:** {f'{base_cv_score:.5f}' if base_cv_score is not None else 'NONE'}
- **Script SHA-256:** `{script_sha256 or 'N/A'}`
- **OOF Parquet SHA-256:** `{oof_sha256 or 'N/A'}`
- **Submission CSV SHA-256:** `{submission_sha256 or 'N/A'}`
- **Git Commit:** `{git_commit or 'N/A'}`
- **Execution:** exit_code={exit_code}, signal={signal}, wall_time={wall_time or 0.0}s, date={timestamp}

## 1. Hypothesis & Feature Specification
{hypothesis}

## 2. Methodology & Code Executed
{methodology}

## 3. Findings
### What Worked
{what_worked}

### What Failed
{what_failed}

## 4. Root Cause Analysis
{why_reasoning}

## 5. Next Steps
{next_steps}
"""
        file_path = self.lessons_dir / f"lesson_{exp_no}.md"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(f"[LessonService] Saved {file_path.name}")

        ingest_status = "NOT INGESTED"
        if self.notebook_client:
            title = f"Lesson Exp {exp_no} [CV: {score_display} | {verdict_str}]"
            res = await self.notebook_client.add_source_file(str(file_path.resolve()), title=title)
            ingest_status = res.get("status", "FAILED")
            logger.info(f"[LessonService] Ingestion to NotebookLM: {ingest_status}")

        lesson_record = {
            "exp_no": exp_no,
            "timestamp": timestamp,
            "status": status,
            "verdict": verdict_str,
            "cv_score": cv_score,
            "fold_scores": fold_scores,
            "base_cv_score": base_cv_score,
            "verdict_info": verdict_info,
            "script_sha256": script_sha256,
            "oof_sha256": oof_sha256,
            "submission_sha256": submission_sha256,
            "git_commit": git_commit,
            "hypothesis": hypothesis,
            "what_worked": what_worked,
            "what_failed": what_failed,
            "why": why_reasoning,
            "next_steps": next_steps,
            "file_path": str(file_path),
            "ingest_status": ingest_status
        }

        return lesson_record
