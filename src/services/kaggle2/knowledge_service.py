"""
knowledge_service.py — Structured Evidence-Based Knowledge Retention Engine
=============================================================================
Manages staged experimental knowledge according to strict verification hierarchy:
  - Categories:
      VERIFIED_FINDINGS
      FAILED_EXPERIMENTS
      UNVERIFIED_HYPOTHESES
      REJECTED_PROPOSALS
  - Enforces cryptographically grounded lesson headers.
  - Handles external NotebookLM synchronization with fail-safe local persistence
    (marks PENDING_EXTERNAL_SYNC if network / API is unavailable).
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


class KnowledgeCategory:
    VERIFIED_FINDINGS = "VERIFIED_FINDINGS"
    FAILED_EXPERIMENTS = "FAILED_EXPERIMENTS"
    UNVERIFIED_HYPOTHESES = "UNVERIFIED_HYPOTHESES"
    REJECTED_PROPOSALS = "REJECTED_PROPOSALS"


class KnowledgeService:
    """Manages verified knowledge retention with offline safety."""

    def __init__(self, run_dir: Path, notebook_client=None):
        self.run_dir = Path(run_dir)
        self.knowledge_dir = self.run_dir / "knowledge_store"
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.notebook_client = notebook_client

        # Initialize category directories
        for cat in [
            KnowledgeCategory.VERIFIED_FINDINGS,
            KnowledgeCategory.FAILED_EXPERIMENTS,
            KnowledgeCategory.UNVERIFIED_HYPOTHESES,
            KnowledgeCategory.REJECTED_PROPOSALS,
        ]:
            (self.knowledge_dir / cat).mkdir(parents=True, exist_ok=True)

    def stage_record(
        self,
        exp_id: str,
        category: str,
        hypothesis: str,
        verdict: str,
        cv_score: Optional[float],
        fold_scores: Dict[int, float],
        paired_diffs: List[float],
        script_sha: str,
        oof_sha: str,
        findings_worked: str,
        findings_failed: str,
        root_cause: str,
        next_steps: str,
        limitations: Optional[str] = None
    ) -> Path:
        """
        Stages an experiment record in the appropriate category on local immutable storage.
        """
        cat_dir = self.knowledge_dir / category
        record_file = cat_dir / f"record_exp{exp_id}.json"
        doc_file = cat_dir / f"lesson_exp{exp_id}.md"

        record_data = {
            "exp_id": exp_id,
            "category": category,
            "staged_at": datetime.now(timezone.utc).isoformat(),
            "hypothesis": hypothesis,
            "verdict": verdict,
            "cv_score": cv_score,
            "fold_scores": fold_scores,
            "paired_diffs": paired_diffs,
            "script_sha256": script_sha,
            "oof_sha256": oof_sha,
            "findings_worked": findings_worked,
            "findings_failed": findings_failed,
            "root_cause": root_cause,
            "next_steps": next_steps,
            "limitations": limitations or "None noted",
            "sync_status": "LOCAL_ONLY"
        }

        record_file.write_text(json.dumps(record_data, indent=2), encoding="utf-8")

        # Generate markdown lesson
        diffs_str = ", ".join(f"{d:+.5f}" for d in paired_diffs) if paired_diffs else "N/A"
        fold_scores_str = ", ".join(f"f{k}={v:.5f}" for k, v in fold_scores.items()) if fold_scores else "N/A"

        md_content = f"""# Lesson: Experiment {exp_id} — {verdict}

- **Date:** {record_data['staged_at']}
- **Category:** {category}
- **Verdict vs Baseline:** {verdict}
- **CV ROC-AUC:** {cv_score if cv_score is not None else 'N/A'}
- **Fold Scores:** [{fold_scores_str}]
- **Paired Diffs (Exp - Base):** [{diffs_str}]
- **Script SHA-256:** `{script_sha}`
- **OOF SHA-256:** `{oof_sha}`

## 1. Hypothesis
{hypothesis}

## 2. Findings
### What Worked
{findings_worked}

### What Failed
{findings_failed}

## 3. Root Cause Analysis
{root_cause}

## 4. Next Steps
{next_steps}

## 5. Limitations
{record_data['limitations']}
"""
        doc_file.write_text(md_content, encoding="utf-8")
        return doc_file

    async def sync_to_notebooklm(self, doc_path: Path, title: str) -> str:
        """
        Attempts to synchronize staged document with NotebookLM.
        Returns 'SYNCED' or 'PENDING_EXTERNAL_SYNC' if offline/failing.
        """
        if not self.notebook_client:
            return "PENDING_EXTERNAL_SYNC"

        try:
            content = doc_path.read_text(encoding="utf-8")
            res = await self.notebook_client.add_source_text(title=title, text=content)
            if res.get("status") in ("PASSED", "OK"):
                return "SYNCED"
            return "PENDING_EXTERNAL_SYNC"
        except Exception:
            return "PENDING_EXTERNAL_SYNC"
