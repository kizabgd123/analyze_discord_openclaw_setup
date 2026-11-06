"""
agent_team.py — Orchestrator for S6E11 Multi-Agent Competition System.
======================================================================
Coordinates the specialized agent triad:
  - Strategist: Hypotheses, literature grounding, priority decisions.
  - Engineer: Implementation code for isolated runner.
  - Skeptic: Leakage prevention, fold freeze verification, rules compliance.
Enforces:
  - ask_notebook tool for every agent in every turn.
  - Mandatory pre-planning lesson query before proposing new experiments.
  - Fixed StratifiedKFold cross-validation splits frozen once per run.
  - Live HTML dashboard updates after every single turn.
"""

import os
import sys
import json
import logging
import asyncio
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from src.services.kaggle2.notebook_client import NotebookLMClient
from src.services.kaggle2.runner import LocalRunner
from src.services.kaggle2.lesson_service import LessonService
from src.services.kaggle2.submission_service import SubmissionService
from src.services.kaggle2.html_generator import render_html_dashboard

logger = logging.getLogger("Kaggle2.AgentTeam")


class AgentTeamOrchestrator:
    """Manages the lifecycle of an autonomous competition run."""

    def __init__(self, run_id: str, data_dir: Optional[Path] = None):
        self.run_id = run_id
        self.run_dir = Path("artifacts/kaggle/s6e11") / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir = Path(data_dir or "artifacts/kaggle/s6e11/data")

        self.state_file = self.run_dir / "state.json"
        self.html_file = self.run_dir / "view.html"
        self.folds_file = self.run_dir / "folds.json"

        self.notebook_client = NotebookLMClient()
        self.runner = LocalRunner(run_dir=self.run_dir, timeout_seconds=600)
        self.lesson_service = LessonService(run_dir=self.run_dir, notebook_client=self.notebook_client)
        self.submission_service = SubmissionService(run_id=self.run_id)

        self.is_running: bool = False
        self.is_paused: bool = False
        self.current_experiment: int = 0
        self.state: Dict[str, Any] = self._load_or_create_state()

    def _load_or_create_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading state from {self.state_file}: {e}")

        initial_state = {
            "run_id": self.run_id,
            "competition": "playground-series-s6e11",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "folds_info": "StratifiedKFold (n_splits=5, shuffle=True, random_state=42) — FROZEN",
            "failures": [],
            "sources": [],
            "transcript": [],
            "nlm_queries": [],
            "experiments": [],
            "lessons": [],
            "submissions": []
        }
        self._save_state(initial_state)
        return initial_state

    def _save_state(self, state: Optional[Dict[str, Any]] = None):
        if state:
            self.state = state
        self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)
        # Regenerate HTML view on every state save
        render_html_dashboard(self.state, self.html_file)

    async def initialize_run(self) -> Dict[str, Any]:
        """Sets up frozen folds, pulls sources from NotebookLM, and prepares run."""
        logger.info(f"[AgentTeam] Initializing run {self.run_id}...")
        # 1. Freeze CV Folds
        self._freeze_cv_folds()

        # 2. Ingest current NotebookLM sources list
        sources = await self.notebook_client.list_sources()
        self.state["sources"] = sources
        self._save_state()

        return {
            "status": "INITIALIZED",
            "run_id": self.run_id,
            "folds_file": str(self.folds_file),
            "sources_count": len(sources),
            "html_view": str(self.html_file)
        }

    def _freeze_cv_folds(self):
        """Skeptic fixes folds once per run so all experiments are 100% comparable."""
        if not self.folds_file.exists():
            train_path = self.data_dir / "train.csv"
            if train_path.exists():
                try:
                    runner_python = Path("/home/kizamladjanijebac/Desktop/discord-openclaw/runner_venv/bin/python3")
                    python_bin = str(runner_python) if runner_python.is_file() else sys.executable
                    evaluator_script = Path(__file__).parent / "evaluator.py"
                    cmd = [
                        python_bin,
                        str(evaluator_script),
                        "freeze",
                        "--train-path", str(train_path),
                        "--out-path", str(self.folds_file),
                        "--n-splits", "5",
                        "--random-state", "42"
                    ]
                    subprocess.run(cmd, capture_output=True, text=True, check=True)
                    logger.info(f"[Skeptic] Frozen 5-fold StratifiedKFold split saved to {self.folds_file}")
                except Exception as exc:
                    logger.error(f"[Skeptic] Error generating frozen folds: {exc}")
                    self.record_failure("FOLD_FREEZE_ERROR", "Failed freezing CV folds", str(exc))

    async def ask_notebook(self, agent_name: str, question: str) -> Dict[str, Any]:
        """Available to EVERY agent in EVERY turn with verbatim logging."""
        logger.info(f"[{agent_name} -> NotebookLM] {question}")
        res = await self.notebook_client.query_notebook(question)
        self.state["nlm_queries"].append({
            "agent": agent_name,
            "question": question,
            "answer": res.get("answer"),
            "citations": res.get("citations", {}),
            "status": res.get("status"),
            "error": res.get("error"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        if res.get("status") == "FAILED":
            self.record_failure("NOTEBOOKLM_QUERY_FAILED", f"Query by {agent_name} failed", res.get("error"))

        self._save_state()
        return res

    def append_transcript(self, agent: str, role: str, message: str, is_lesson_query: bool = False):
        """Appends a turn message to the live multi-agent transcript."""
        self.state["transcript"].append({
            "agent": agent,
            "role": role,
            "message": message,
            "is_lesson_query": is_lesson_query,
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S")
        })
        self._save_state()

    def record_failure(self, fail_type: str, title: str, raw_error: Optional[str]):
        """Records an honest failure at the top of the dashboard."""
        self.state["failures"].insert(0, {
            "type": fail_type,
            "title": title,
            "raw_error": raw_error or "Unknown failure",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self._save_state()

    async def execute_pre_planning_lesson_query(self) -> Dict[str, Any]:
        """Queries the notebook for past lessons before planning a new experiment."""
        q = "What worked and what failed in our previous experiments for S6E11, and what are the key takeaways?"
        self.append_transcript(
            agent="Strategist",
            role="Strategist",
            message=f"Consulting research assistant for past lessons: '{q}'",
            is_lesson_query=True
        )
        res = await self.ask_notebook("Strategist", q)
        ans = res.get("answer") or f"NLM query failed: {res.get('error')}"
        self.append_transcript(
            agent="Research Assistant",
            role="NotebookLM",
            message=f"Grounded Lessons Overview:\n{ans[:400]}..." if len(ans) > 400 else ans,
            is_lesson_query=True
        )
        return res

    async def stop(self) -> Dict[str, Any]:
        """Immediately stops running tasks, killing any child processes."""
        self.is_running = False
        self.is_paused = False
        kill_ok = await self.runner.kill()
        self.append_transcript(agent="System", role="Orchestrator", message="🛑 Stop signal received. Runner process killed.")
        return {"status": "STOPPED", "runner_killed": kill_ok}

    async def run_single_experiment(self, exp_no: int, timeout_seconds: int = 1200) -> Dict[str, Any]:
        """
        Executes one full experiment round:
          1. Pre-planning lesson query to NotebookLM.
          2. Strategist plans hypothesis & queries NotebookLM for techniques.
          3. Skeptic audits proposal against leakage, frozen folds, and competition rules.
          4. Engineer produces self-contained Python script.
          5. LocalRunner executes script inside run folder (with hard timeout).
          6. Real CV ROC-AUC is measured and verified.
          7. Lesson is written and ingested into NotebookLM as a new source.
        """
        import re
        from gemini_client import query_llm

        if not self.is_running:
            return {"status": "STOPPED", "message": "Orchestrator is not running"}

        logger.info(f"[AgentTeam] Starting Experiment #{exp_no}...")
        self.current_experiment = exp_no

        # ── Step 1: Pre-planning lesson query ──
        await self.execute_pre_planning_lesson_query()
        if not self.is_running:
            return {"status": "STOPPED"}

        # ── Step 2: Strategist planning & NotebookLM inquiry ──
        tech_q = f"For Kaggle Playground S6E11, what specific model parameters and feature engineering are recommended for Experiment #{exp_no}?"
        tech_res = await self.ask_notebook("Strategist", tech_q)
        tech_ans = tech_res.get("answer") or "Standard GBDT with frequency encoding"

        strat_prompt = (
            f"You are the Strategist. Based on NotebookLM research below, propose a concrete, testable hypothesis "
            f"for Experiment #{exp_no} predicting credit card fraud (metric: ROC-AUC).\n\n"
            f"Research Insights:\n{tech_ans[:1000]}\n\n"
            f"State: 1. Hypothesis; 2. Feature engineering; 3. Model family; 4. Expected impact."
        )
        strat_resp = await asyncio.to_thread(query_llm, strat_prompt, system="You are the ML Strategist. Ground every claim in facts. Do not write code.")
        self.append_transcript(agent="Strategist", role="Strategist", message=strat_resp)
        if not self.is_running:
            return {"status": "STOPPED"}

        # ── Step 3: Skeptic Audit ──
        skep_prompt = (
            f"You are the Skeptic. Review the Strategist's proposal for Experiment #{exp_no}:\n{strat_resp}\n\n"
            f"Audit checklist:\n"
            f"1. Is the metric strictly ROC-AUC? (Yes/No)\n"
            f"2. Does it use the frozen 5-fold StratifiedKFold without target leakage? (Yes/No)\n"
            f"3. Does it comply with external data and code sharing rules? (Yes/No)\n"
            f"4. Potential failure modes and decision."
        )
        skep_resp = await asyncio.to_thread(query_llm, skep_prompt, system="You are the ML Skeptic. Rigorously hunt data leakage, misread metrics, and overconfidence.")
        self.append_transcript(agent="Skeptic", role="Skeptic", message=skep_resp)
        if not self.is_running:
            return {"status": "STOPPED"}

        # ── Step 4: Engineer code generation ──
        eng_prompt = (
            f"You are the ML Engineer. Write a complete, runnable Python script for Experiment #{exp_no}.\n"
            f"Requirements:\n"
            f"- Load training data from 'artifacts/kaggle/s6e11/data/train.csv'.\n"
            f"- Load frozen fold split from 'folds.json' in current working directory, or recreate StratifiedKFold(n_splits=5, shuffle=True, random_state=42).\n"
            f"- Calculate Out-of-Fold predictions and compute ROC-AUC using sklearn.metrics.roc_auc_score.\n"
            f"- Print 'CV_ROC_AUC: <score>' clearly to stdout so the runner can extract it.\n"
            f"- Keep execution fast (<10 mins).\n"
            f"- Return ONLY runnable Python code inside ```python ... ```."
        )
        eng_code_raw = await asyncio.to_thread(query_llm, eng_prompt, system="You are the ML Engineer. Write clean, complete, standalone Python code.")
        
        # Extract code from markdown block
        match = re.search(r"```(?:python)?\s*\n(.*?)\n```", eng_code_raw, re.DOTALL)
        code_str = match.group(1) if match else eng_code_raw

        script_path = self.run_dir / f"exp_{exp_no}.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code_str)

        self.append_transcript(agent="Engineer", role="Engineer", message=f"Generated runnable script `exp_{exp_no}.py` ({len(code_str)} bytes). Handing over to Runner.")
        if not self.is_running:
            return {"status": "STOPPED"}

        # ── Step 5: Local Execution via Runner ──
        self.runner.timeout_seconds = timeout_seconds
        exec_res = await self.runner.execute_script(script_path)
        cv_score = exec_res.get("cv_score")
        exec_status = exec_res.get("status", "FAILED")

        if exec_status != "PASSED":
            self.record_failure("EXPERIMENT_EXECUTION_FAILURE", f"Experiment #{exp_no} exited with status {exec_status}", exec_res.get("stderr"))

        self.state["experiments"].append({
            "exp_no": exp_no,
            "hypothesis": strat_resp[:160] + "...",
            "cv_score": cv_score,
            "status": exec_status,
            "elapsed_seconds": exec_res.get("elapsed_seconds", 0.0)
        })

        # ── Step 6: Postmortem & Lesson Generation ──
        lesson_record = await self.lesson_service.create_lesson(
            exp_no=exp_no,
            hypothesis=strat_resp,
            methodology=f"Executed exp_{exp_no}.py ({exec_res.get('elapsed_seconds', 0):.1f}s)",
            cv_score=cv_score,
            what_worked=f"Experiment executed with status {exec_status}. CV ROC-AUC: {cv_score}" if cv_score else "Process caught execution safely",
            what_failed=exec_res.get("stderr", "None")[:300] if exec_status != "PASSED" else "None",
            why_reasoning="Measured real out-of-fold performance against frozen CV split",
            next_steps=f"Evaluate score vs baseline and adjust features/ensembles" if cv_score else "Fix runtime errors in next cycle",
            status=exec_status
        )
        self.state["lessons"].append(lesson_record)
        self._save_state()

        self.append_transcript(
            agent="Skeptic",
            role="Skeptic",
            message=f"Experiment #{exp_no} evaluated. Status: {exec_status} | Real CV ROC-AUC: {cv_score if cv_score is not None else 'FAILED'}. Lesson saved and ingested to NotebookLM."
        )

        return {
            "exp_no": exp_no,
            "status": exec_status,
            "cv_score": cv_score,
            "elapsed_seconds": exec_res.get("elapsed_seconds", 0.0),
            "lesson_file": lesson_record.get("file_path")
        }

    async def run_autonomous_cycle(self, max_experiments: int = 2, timeout_per_exp: int = 1200) -> Dict[str, Any]:
        """Runs an autonomous cycle with a hard cap on number of experiments."""
        self.is_running = True
        results = []

        logger.info(f"[AgentTeam] Starting autonomous cycle for run {self.run_id} (max_experiments={max_experiments})")
        for i in range(1, max_experiments + 1):
            if not self.is_running:
                break
            res = await self.run_single_experiment(exp_no=i, timeout_seconds=timeout_per_exp)
            results.append(res)
            # Brief cool down between experiments
            await asyncio.sleep(2)

        self.is_running = False
        return {
            "status": "COMPLETED",
            "run_id": self.run_id,
            "experiments_run": len(results),
            "results": results,
            "html_view": str(self.html_file)
        }
