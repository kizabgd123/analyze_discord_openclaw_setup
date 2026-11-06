"""
lesson_service.py — Structured Lesson Generation & NotebookLM Ingestion.
========================================================================
After every experiment, produces a structured postmortem lesson markdown,
saves it to artifacts/kaggle/s6e11/<run_id>/lessons/, and ingests it back
into the NotebookLM notebook as a new source for future experiment planning.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
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
        status: str = "PASSED"
    ) -> Dict[str, Any]:
        """
        Creates a structured lesson, writes it to disk, and ingests into NotebookLM.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        score_display = f"{cv_score:.5f}" if cv_score is not None else "NOT RUN / FAILED"

        content = f"""# Lesson: Experiment {exp_no} — {status}

- **Date:** {timestamp}
- **Status:** {status}
- **Real CV ROC-AUC:** {score_display}

## 1. Hypothesis
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
            title = f"Lesson Exp {exp_no} [CV: {score_display}]"
            res = await self.notebook_client.add_source_file(str(file_path.resolve()), title=title)
            ingest_status = res.get("status", "FAILED")
            logger.info(f"[LessonService] Ingestion to NotebookLM: {ingest_status}")

        lesson_record = {
            "exp_no": exp_no,
            "timestamp": timestamp,
            "status": status,
            "cv_score": cv_score,
            "hypothesis": hypothesis,
            "what_worked": what_worked,
            "what_failed": what_failed,
            "why": why_reasoning,
            "next_steps": next_steps,
            "file_path": str(file_path),
            "ingest_status": ingest_status
        }

        return lesson_record
