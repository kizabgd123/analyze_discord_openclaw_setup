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
import re
import json
import shutil
import hashlib
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
from src.services.kaggle2.debate_engine import DebateEngine, hash_text, parse_llm_json

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
        self.debate_engine = DebateEngine(model_name="claude-sonnet-4-6", account="999@mrcleanervracar.com")
        from src.services.kaggle2.baton_manager import BatonManager
        self.baton_manager = BatonManager(run_dir=self.run_dir)
        self.baton_manager.initialize_cookbooks()
        self.authoritative_fold_hash = "bb6cda09006260033590976687e28c1f73ec418812ce5240988f12cd207c1db3"

        self.is_running: bool = False
        self.is_paused: bool = False
        self.current_experiment: int = 0
        self.exp_nlm_queries: int = 0
        self.exp_nlm_time: float = 0.0
        self.state: Dict[str, Any] = self._load_or_create_state()

    def _load_or_create_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "blocked_hypotheses" not in data:
                        data["blocked_hypotheses"] = []
                    if "debug_attempts" not in data:
                        data["debug_attempts"] = []
                    return data
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
            "blocked_hypotheses": [],
            "debug_attempts": [],
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
        if hasattr(self, "baton_manager"):
            self.baton_manager.update_baton(self.state)

    async def initialize_run(self) -> Dict[str, Any]:
        """Sets up frozen folds, pulls sources from NotebookLM, seeds reference baseline, and prepares run."""
        logger.info(f"[AgentTeam] Initializing run {self.run_id}...")
        # 1. Freeze CV Folds
        self._freeze_cv_folds()

        # 2. Seed verified Exp 0 Reference Baseline if not already present
        if not any(e.get("exp_no") == 0 for e in self.state.get("experiments", [])):
            self.state["experiments"].insert(0, {
                "exp_no": 0,
                "hypothesis": "Exp 0 Reference Baseline (LightGBM on 24 raw features, frozen 5-fold CV, 50 rounds early stopping)",
                "skeptic_verdict": "BASELINE",
                "deciding_reason": "Audited reference baseline",
                "code": "# Exp 0 Baseline Reference — LightGBM on 24 features",
                "cv_score": 0.94557,
                "fold_scores": {"0": 0.94313, "1": 0.94721, "2": 0.95028, "3": 0.94641, "4": 0.94134},
                "verdict_vs_base": "BASELINE",
                "paired_diffs": [0.0, 0.0, 0.0, 0.0, 0.0],
                "status": "PASSED",
                "exit_code": 0,
                "signal": None,
                "debug_attempts": 0,
                "phase_timings": {"nlm_seconds": 0, "runner_seconds": 166.0},
                "elapsed_seconds": 166.0,
                "script_sha256": "baseline_exp0_reference",
                "oof_sha256": "b630ff389990882b65a2a089d1bb266b873973eed9f9e0adaa0baa0a09ed338a",
                "submission_sha256": None,
                "git_commit": "reference"
            })

        # 3. Ingest current NotebookLM sources list
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

    async def ask_notebook(self, agent_name: str, question: str, reason: str = "general") -> Dict[str, Any]:
        """Available to EVERY agent in EVERY turn with verbatim logging, budget control and latency tracking."""
        if self.exp_nlm_queries >= 4:
            logger.warning(f"[NotebookLM Budget] Query cap reached (4 max) for Exp #{self.current_experiment}. Skipping '{question}'")
            return {"status": "SKIPPED", "answer": None, "error": "Query budget reached (4 per experiment limit)"}

        if self.exp_nlm_time >= 300.0:
            logger.warning(f"[NotebookLM Budget] Time cap reached (5 min max) for Exp #{self.current_experiment}. Skipping '{question}'")
            return {"status": "SKIPPED", "answer": None, "error": "Query time budget reached (300s cumulative limit)"}

        start_t = asyncio.get_event_loop().time()
        logger.info(f"[{agent_name} -> NotebookLM] ({reason}) {question}")
        res = await self.notebook_client.query_notebook(question)
        latency = asyncio.get_event_loop().time() - start_t

        self.exp_nlm_queries += 1
        self.exp_nlm_time += latency

        self.state["nlm_queries"].append({
            "exp_no": self.current_experiment,
            "agent": agent_name,
            "reason": reason,
            "question": question,
            "answer": res.get("answer"),
            "citations": res.get("citations", {}),
            "status": res.get("status"),
            "error": res.get("error"),
            "latency_seconds": round(latency, 2),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        if res.get("status") == "FAILED":
            self.record_failure("NOTEBOOKLM_QUERY_FAILED", f"Query by {agent_name} failed: {question[:60]}", res.get("error"))

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
        q = "BRIEF: What worked, what failed, and what was harness-verified in previous S6E11 experiments?"
        self.append_transcript(
            agent="Strategist",
            role="Strategist",
            message=f"Consulting research assistant for past lessons: '{q}'",
            is_lesson_query=True
        )
        res = await self.ask_notebook("Strategist", q, reason="lessons_review")
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
        Executes one full experiment round with Debate with Teeth and Debug Loop:
          1. Pre-planning lesson query to NotebookLM.
          2. Strategist formulates dynamic question to NotebookLM & plans hypothesis (filtering past blocked/tested).
          3. Skeptic audits with fact-check query and structured verdict (BLOCK / PROCEED_WITH_CONDITIONS / PROCEED).
          4. Debate resolution: On BLOCK, Strategist answers point-by-point, Skeptic renders final verdict.
             If still BLOCKED, Engineer does NOT run, and BLOCKED state is recorded.
          5. Engineer produces model_part.py against fixed Scaffold contract with minimal example.
          6. Scaffold runner executes 5-fold CV inside Firejail sandbox.
          7. Debug Loop: If execution fails, up to 2 fix attempts with raw stderr/stdout feedback.
          8. Harness evaluates OOF predictions outside sandbox deterministically.
          9. Honest lesson generated and recorded.
        """
        import re
        from gemini_client import query_llm, query_llm_with_lineage, LLMResponse

        if not self.is_running:
            return {"status": "STOPPED", "message": "Orchestrator is not running"}

        logger.info(f"[AgentTeam] Starting Experiment #{exp_no}...")
        self.current_experiment = exp_no
        self.exp_nlm_queries = 0
        self.exp_nlm_time = 0.0
        exp_start_time = asyncio.get_event_loop().time()
        phase_timings = {"nlm_seconds": 0.0, "runner_seconds": 0.0}

        # ── Step 1: Pre-planning lesson query ──
        nlm_t0 = asyncio.get_event_loop().time()
        await self.execute_pre_planning_lesson_query()
        phase_timings["nlm_seconds"] += round(asyncio.get_event_loop().time() - nlm_t0, 2)
        if not self.is_running:
            return {"status": "STOPPED"}

        # ── Step 2: Strategist planning & NotebookLM inquiry ──
        past_hyps = [e.get("hypothesis", "") for e in self.state.get("experiments", [])]
        blocked_hyps = self.state.get("blocked_hypotheses", [])

        # Strategist formulates a question dynamically
        strat_q_prompt = (
            f"You are the ML Strategist for Kaggle S6E11 (credit card fraud, ROC-AUC). "
            f"Previous experiments: {json.dumps(past_hyps[-2:])}. "
            f"Blocked ideas: {json.dumps(blocked_hyps[-2:])}. "
            f"Formulate ONE specific research question to ask the notebook assistant for Experiment #{exp_no}. "
            f"Prefix it with BRIEF:, DEEP:, or CHECK:."
        )
        raw_strat_q = await asyncio.to_thread(query_llm, strat_q_prompt, system="Formulate only the question string.")
        strat_q = raw_strat_q.strip().splitlines()[0].strip('"').strip("'") if raw_strat_q else ""
        if not any(strat_q.startswith(p) for p in ("BRIEF:", "DEEP:", "CHECK:")):
            strat_q = f"BRIEF: {strat_q}" if strat_q else "BRIEF: What model families and feature encodings perform best for fraud detection?"

        nlm_t0 = asyncio.get_event_loop().time()
        tech_res = await self.ask_notebook("Strategist", strat_q, reason="strategist_technique_search")
        phase_timings["nlm_seconds"] += round(asyncio.get_event_loop().time() - nlm_t0, 2)
        tech_ans = tech_res.get("answer") or "Standard GBDT with categorical frequency encoding"

        # Identify baseline from state if available
        exp0_rec = next((e for e in self.state.get("experiments", []) if e.get("exp_no") == 0), None)
        base_cv_val = exp0_rec.get("cv_score", 0.94557) if exp0_rec and exp0_rec.get("cv_score") else 0.94557
        base_cv_str = f"{base_cv_val:.5f}"

        # Stage 1: Build Strategist Proposal Prompt conforming to structured schema
        strat_prompt = self.debate_engine.build_strategist_proposal_prompt(
            exp_no=exp_no,
            verified_columns=None,
            baseline_metric=base_cv_val,
            literature_context=tech_ans[:3500]
        )
        strat_prompt_sha = hash_text(strat_prompt)
        strat_resp_obj = await asyncio.to_thread(
            query_llm_with_lineage,
            strat_prompt,
            system="You are the ML Strategist. Ground every claim in facts. Do not write code."
        )
        strat_resp = strat_resp_obj.text if isinstance(strat_resp_obj, LLMResponse) else str(strat_resp_obj)
        lineage_model = strat_resp_obj.model if isinstance(strat_resp_obj, LLMResponse) else "unknown"
        lineage_account = strat_resp_obj.account if isinstance(strat_resp_obj, LLMResponse) else None
        lineage_provider = strat_resp_obj.provider if isinstance(strat_resp_obj, LLMResponse) else "unknown"

        self.append_transcript(agent="Strategist", role="Strategist", message=strat_resp)
        if not self.is_running:
            return {"status": "STOPPED"}

        # Parse and validate proposal
        prop_dict = parse_llm_json(strat_resp)
        if not prop_dict:
            prop_dict = self.debate_engine.adapt_legacy_proposal_text(strat_resp, exp_no)

        val_ok, val_err = self.debate_engine.validate_strategist_proposal(prop_dict)
        if not val_ok:
            logger.warning(f"[Strategist Proposal Validation] Error: {val_err}")
            if "UngroundedFeatureError" in val_err or "TargetLeakageError" in val_err:
                self.record_failure("STRATEGIST_PROPOSAL_REJECTED", f"Exp #{exp_no} proposal rejected", val_err)
                elapsed = asyncio.get_event_loop().time() - exp_start_time
                self.state["blocked_hypotheses"].append(prop_dict.get("hypothesis", strat_resp[:200]))
                self.state["experiments"].append({
                    "exp_no": exp_no,
                    "hypothesis": prop_dict.get("hypothesis", strat_resp[:160] + "..."),
                    "hypothesis_id": prop_dict.get("hypothesis_id", f"EXP{exp_no}_HYPOTHESIS"),
                    "skeptic_verdict": "BLOCK",
                    "deciding_reason": val_err,
                    "cv_score": None,
                    "status": "BLOCKED",
                    "exit_code": None,
                    "signal": None,
                    "debug_attempts": 0,
                    "phase_timings": phase_timings,
                    "elapsed_seconds": round(elapsed, 2),
                    "debate_lineage": {
                        "hypothesis_id": prop_dict.get("hypothesis_id", f"EXP{exp_no}_HYPOTHESIS"),
                        "model": lineage_model,
                        "account": lineage_account,
                        "provider": lineage_provider,
                        "prompt_sha256": {"proposal": strat_prompt_sha},
                        "policy_gate": {"authorized": False, "reason": val_err}
                    }
                })
                self._save_state()
                return {
                    "exp_no": exp_no,
                    "status": "BLOCKED",
                    "cv_score": None,
                    "elapsed_seconds": round(elapsed, 2)
                }

        # ── Step 3: Skeptic Audit (Stage 2: Numbered Objections) ──
        skep_check_q = f"CHECK: What evidence in competition notes or literature supports or contradicts: '{strat_resp[:120]}'?"
        nlm_t0 = asyncio.get_event_loop().time()
        skep_check_res = await self.ask_notebook("Skeptic", skep_check_q, reason="skeptic_fact_check")
        phase_timings["nlm_seconds"] += round(asyncio.get_event_loop().time() - nlm_t0, 2)
        skep_check_ans = skep_check_res.get("answer") or ""

        skep_prompt = self.debate_engine.build_skeptic_review_prompt(
            proposal_dict=prop_dict,
            exp_no=exp_no,
            fact_check_context=skep_check_ans[:600]
        )
        skep_prompt_sha = hash_text(skep_prompt)
        skep_resp = await asyncio.to_thread(
            query_llm,
            skep_prompt,
            system="You are the ML Skeptic. Enforce strict leakage and rule integrity."
        )
        self.append_transcript(agent="Skeptic", role="Skeptic", message=skep_resp)
        if not self.is_running:
            return {"status": "STOPPED"}

        def _parse_verdict(text: str) -> str:
            m = re.search(r"(?:FINAL_)?VERDICT:\s*(BLOCK|PROCEED_WITH_CONDITIONS|PROCEED|APPROVE|REJECT|NEEDS_EVIDENCE)", text, re.IGNORECASE)
            if m:
                v = m.group(1).upper()
                if v == "BLOCK": return "BLOCK"
                if v == "REJECT": return "BLOCK"
                if v in ("PROCEED_WITH_CONDITIONS", "NEEDS_EVIDENCE"): return "PROCEED_WITH_CONDITIONS"
                return "PROCEED"
            upper = text.upper()
            if "BLOCK" in upper[:40] or upper.startswith("BLOCK") or "REJECT" in upper[:40]:
                return "BLOCK"
            if "CONDITION" in upper[:80] or "NEEDS_EVIDENCE" in upper[:80]:
                return "PROCEED_WITH_CONDITIONS"
            return "BLOCK"

        def _parse_reason(text: str) -> str:
            m = re.search(r"(?:DECIDING_REASON|FINAL_REASON|REASON):\s*(.*)", text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
            lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
            return lines[-1] if lines else "Debate consensus"

        skep_review = parse_llm_json(skep_resp)
        if not skep_review:
            skep_review = self.debate_engine.adapt_legacy_review_text(skep_resp, exp_no)

        initial_verdict = _parse_verdict(skep_resp)
        final_verdict = initial_verdict
        deciding_reason = _parse_reason(skep_resp)
        rebut_prompt_sha = None
        rebut_resp = ""
        rebut_dict = None
        final_skep_prompt_sha = None
        final_skep_resp = ""
        final_skep_review = None

        # ── Stage 3 & 4: Rebuttal & Final Review ──
        if initial_verdict == "BLOCK" or skep_review.get("overall_verdict") in ("REJECT", "NEEDS_EVIDENCE"):
            # Turn 3: Strategist answers point by point
            rebut_prompt = self.debate_engine.build_strategist_rebuttal_prompt(
                proposal_dict=prop_dict,
                skeptic_review=skep_review,
                exp_no=exp_no
            )
            rebut_prompt_sha = hash_text(rebut_prompt)
            rebut_resp = await asyncio.to_thread(query_llm, rebut_prompt, system="You are the Strategist. Rebut or revise.")
            self.append_transcript(agent="Strategist", role="Strategist", message=rebut_resp)
            rebut_dict = parse_llm_json(rebut_resp)

            # Turn 4: Skeptic final verdict
            final_skep_prompt = self.debate_engine.build_skeptic_final_prompt(
                skeptic_review=skep_review,
                strategist_rebuttal=rebut_dict or {"rebuttal_text": rebut_resp},
                exp_no=exp_no
            )
            final_skep_prompt_sha = hash_text(final_skep_prompt)
            final_skep_resp = await asyncio.to_thread(query_llm, final_skep_prompt, system="You are the Skeptic. Render final verdict.")
            self.append_transcript(agent="Skeptic", role="Skeptic", message=final_skep_resp)
            final_verdict = _parse_verdict(final_skep_resp)
            deciding_reason = _parse_reason(final_skep_resp)

            final_skep_review = parse_llm_json(final_skep_resp)
            if not final_skep_review:
                final_skep_review = self.debate_engine.adapt_legacy_final_text(
                    final_skep_resp,
                    exp_no,
                    original_objections=skep_review.get("objections", [])
                )
        else:
            final_skep_review = {
                "hypothesis_id": prop_dict.get("hypothesis_id", f"EXP{exp_no}_HYPOTHESIS"),
                "objection_resolutions": [],
                "final_verdict": "APPROVE",
                "deciding_reason": skep_review.get("summary", "Proposal approved on initial review")
            }

        # Turn 5: Strategist states formal decision and deciding reason
        strat_dec_prompt = (
            f"The Skeptic rendered final verdict: {final_verdict} (Reason: {deciding_reason}).\n"
            f"State your formal decision and deciding reason:\n"
            f"DECISION: {'BLOCKED' if final_verdict == 'BLOCK' else 'PROCEED'}\n"
            f"DECIDING_REASON: <concise summary>"
        )
        strat_dec_resp = await asyncio.to_thread(query_llm, strat_dec_prompt, system="You are the Strategist. State final decision.")
        self.append_transcript(agent="Strategist", role="Strategist", message=strat_dec_resp)
        deciding_reason = _parse_reason(strat_dec_resp) or deciding_reason

        # ── Stage 5: Deterministic Policy Gate ──
        gate_ok, gate_reason = self.debate_engine.evaluate_policy_gate(
            final_skep_review,
            original_objections=skep_review.get("objections", [])
        )

        debate_lineage = {
            "hypothesis_id": prop_dict.get("hypothesis_id", f"EXP{exp_no}_HYPOTHESIS"),
            "model": lineage_model,
            "account": lineage_account,
            "provider": lineage_provider,
            "prompt_sha256": {
                "proposal": strat_prompt_sha,
                "review": skep_prompt_sha,
                "rebuttal": rebut_prompt_sha,
                "final_review": final_skep_prompt_sha
            },
            "objections": skep_review.get("objections", []),
            "rebuttals": rebut_dict.get("rebuttals", []) if rebut_dict else [],
            "resolutions": final_skep_review.get("objection_resolutions", []),
            "policy_gate": {
                "authorized": gate_ok and final_verdict != "BLOCK",
                "reason": gate_reason if not gate_ok else deciding_reason
            }
        }

        # ── Enforcement: On BLOCK / Policy Gate Violation, Engineer does NOT start ──
        if final_verdict == "BLOCK" or not gate_ok:
            final_block_reason = gate_reason if not gate_ok else deciding_reason
            logger.warning(f"[AgentTeam] Experiment #{exp_no} BLOCKED by Skeptic / Policy Gate: {final_block_reason}. Skipping Engineer.")
            self.state["blocked_hypotheses"].append(prop_dict.get("hypothesis", strat_resp[:200]))
            self.record_failure("EXPERIMENT_BLOCKED", f"Experiment #{exp_no} BLOCKED by Skeptic / Policy Gate", final_block_reason)

            elapsed = asyncio.get_event_loop().time() - exp_start_time
            self.state["experiments"].append({
                "exp_no": exp_no,
                "hypothesis": prop_dict.get("hypothesis", strat_resp[:160] + "..."),
                "hypothesis_id": prop_dict.get("hypothesis_id", f"EXP{exp_no}_HYPOTHESIS"),
                "skeptic_verdict": "BLOCK",
                "deciding_reason": final_block_reason,
                "cv_score": None,
                "status": "BLOCKED",
                "exit_code": None,
                "signal": None,
                "debug_attempts": 0,
                "phase_timings": phase_timings,
                "elapsed_seconds": round(elapsed, 2),
                "debate_lineage": debate_lineage
            })

            lesson_record = await self.lesson_service.create_lesson(
                run_id=self.run_id,
                exp_no=exp_no,
                hypothesis=strat_resp,
                methodology="NOT RUN — Blocked during debate stage",
                cv_score=None,
                what_worked="Debate gate caught invalid proposal before wasting compute",
                what_failed=f"Blocked due to: {final_block_reason}",
                why_reasoning="Hypothesis violated competition constraints or literature consistency",
                next_steps="Reformulate hypothesis to comply with frozen fold protocol and sandbox limits",
                status="BLOCKED"
            )
            self.state["lessons"].append(lesson_record)
            self._save_state()
            return {
                "exp_no": exp_no,
                "status": "BLOCKED",
                "cv_score": None,
                "elapsed_seconds": round(elapsed, 2),
                "lesson_file": lesson_record.get("file_path")
            }

        # ── Step 4: Engineer code generation (Scaffold Contract) ──
        if initial_verdict == "BLOCK" and rebut_resp:
            active_spec = (
                f"INITIAL PROPOSAL (NOTE: WAS CRITIQUED/BLOCKED BY SKEPTIC):\n{strat_resp}\n\n"
                f"REVISED SPECIFICATION & COMMITMENTS (MANDATORY TO FOLLOW):\n{rebut_resp}\n\n"
                f"SKEPTIC FINAL CONDITIONS & DECIDING REASON:\n{deciding_reason}"
            )
        else:
            active_spec = (
                f"HYPOTHESIS & FEATURE SPECIFICATION:\n{strat_resp}\n\n"
                f"DECIDING REASON & CONDITIONS:\n{deciding_reason}"
            )

        eng_prompt = f"""You are the ML Engineer. Write `model_part.py` for Experiment #{exp_no}.
Specification & Approved Debate Protocol:
{active_spec}

CRITICAL REQUIREMENT:
If the debate revised the proposal, eliminated features, or set conditions (e.g., forbidding specific collapsed interactions, non-existent columns, or leakage), you MUST strictly follow the REVISED specification! DO NOT write forbidden or removed code.

ARCHITECTURE CONTRACT (MANDATORY):
A fixed scaffold handles data loading from train.csv (699,960 rows), frozen 5-fold StratifiedKFold alignment,
and out-of-fold prediction saving.
NOTE ON PREVIOUS CRASH: In Exp 1, the script crashed with ValueError converting 'scheme' to int. The scaffold runner now handles folds.json safely and isolates fold indices.
Your file `model_part.py` MUST define:
```python
def train_predict(X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series) -> np.ndarray:
    # Train your model on (X_train, y_train)
    # Return 1D numpy array of probabilities P(is_fraud=1) for X_val in [0.0, 1.0]
```

DATASET SCHEMA:
- Features include numericals (amount_usd, account_balance_usd, etc.) and categoricals/booleans (merchant_category, card_type, channel, device_type, etc.).
- Ensure categorical and boolean columns are converted with .astype('category') or encoded before fitting.

MINIMAL WORKING EXAMPLE:
```python
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier

def train_predict(X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series) -> np.ndarray:
    cat_cols = X_train.select_dtypes(include=['object', 'category', 'bool']).columns.tolist()
    for col in cat_cols:
        X_train[col] = X_train[col].astype('category')
        X_val[col] = X_val[col].astype('category')

    model = LGBMClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=6,
        random_state=42,
        n_jobs=-1,
        verbose=-1
    )
    model.fit(X_train, y_train)
    return model.predict_proba(X_val)[:, 1]
```
Return ONLY the runnable Python code for `model_part.py` inside ```python ... ```.
"""
        eng_code_raw = await asyncio.to_thread(query_llm, eng_prompt, system="You are the ML Engineer. Return only valid python code.")
        match = re.search(r"```(?:python)?\s*\n(.*?)\n```", eng_code_raw, re.DOTALL)
        code_str = match.group(1) if match else eng_code_raw

        model_module_path = self.run_dir / "model_part.py"
        with open(model_module_path, "w", encoding="utf-8") as f:
            f.write(code_str)

        # Preserve per-experiment code module
        exp_module_path = self.run_dir / f"model_part_exp{exp_no}.py"
        with open(exp_module_path, "w", encoding="utf-8") as f:
            f.write(code_str)

        # Copy fixed scaffold into run_dir
        scaffold_src = Path(__file__).parent / "scaffold_runner.py"
        scaffold_dst = self.run_dir / "run_scaffold.py"
        shutil.copyfile(scaffold_src, scaffold_dst)

        self.append_transcript(agent="Engineer", role="Engineer", message=f"Generated `model_part.py` ({len(code_str)} bytes) conforming to Scaffold contract.")
        if not self.is_running:
            return {"status": "STOPPED"}

        # ── Step 5: Execution & Debug Loop ──
        self.runner.timeout_seconds = timeout_seconds
        oof_file = self.run_dir / f"oof_exp{exp_no}.parquet"
        cmd_args = [
            "--run-dir", str(self.run_dir.resolve()),
            "--data-dir", str(self.data_dir.resolve()),
            "--folds-file", str((self.folds_file or (self.run_dir / "folds.json")).resolve()),
            "--model-module", str(model_module_path.resolve()),
            "--exp-no", str(exp_no)
        ]

        # Pre-Execution Integrity Gate: AST Leakage & Fold Tampering
        val_res = self.runner.validate_pre_execution(
            model_script=model_module_path,
            manifest_file=self.run_dir / "manifest.json" if (self.run_dir / "manifest.json").exists() else None,
            authoritative_fold_hash=self.authoritative_fold_hash
        )
        if not val_res.get("passed", False):
            block_reasons = "; ".join(val_res.get("errors", []))
            logger.error(f"[AgentTeam] Exp #{exp_no} BLOCKED PRE-EXECUTION: {block_reasons}")
            self.record_failure("PRE_EXECUTION_INTEGRITY_VIOLATION", f"Exp #{exp_no} blocked by AST/Fold gate", block_reasons)
            elapsed = asyncio.get_event_loop().time() - exp_start_time
            self.state["experiments"].append({
                "exp_no": exp_no,
                "hypothesis": prop_dict.get("hypothesis", strat_resp[:160] + "..."),
                "hypothesis_id": prop_dict.get("hypothesis_id", f"EXP{exp_no}_HYPOTHESIS"),
                "skeptic_verdict": "BLOCK_PRE_EXEC",
                "deciding_reason": block_reasons,
                "code": code_str,
                "cv_score": None,
                "fold_scores": {},
                "verdict_vs_base": "BLOCKED",
                "paired_diffs": [],
                "status": "BLOCKED_PRE_EXECUTION",
                "exit_code": None,
                "signal": None,
                "debug_attempts": 0,
                "phase_timings": phase_timings,
                "elapsed_seconds": round(elapsed, 2),
                "script_sha256": hash_text(code_str),
                "oof_sha256": None,
                "submission_sha256": None,
                "git_commit": None,
                "debate_lineage": debate_lineage
            })
            self._save_state()
            return {
                "exp_no": exp_no,
                "status": "BLOCKED_PRE_EXECUTION",
                "cv_score": None,
                "error": block_reasons
            }

        runner_start = asyncio.get_event_loop().time()
        exec_res = await self.runner.execute_script(scaffold_dst, args=cmd_args, verify_oof=True, oof_file=oof_file)
        exec_status = exec_res.get("status", "FAILED")
        cv_score = exec_res.get("cv_score")
        fold_scores = exec_res.get("fold_scores", {})
        debug_attempts = 0
        max_debug_attempts = 2

        while exec_status != "PASSED" and debug_attempts < max_debug_attempts and self.is_running:
            debug_attempts += 1
            err_msg = exec_res.get("last_stderr") or exec_res.get("error") or "Unknown execution error"
            recent_stdout = exec_res.get("last_stdout") or ""
            logger.warning(f"[Engineer Debug Loop] Exp #{exp_no} Attempt #{debug_attempts}/2. Error: {err_msg[:200]}")

            fix_prompt = f"""The model script failed inside the sandbox runner with the following error:
ERROR:
{err_msg}

RECENT STDOUT:
{recent_stdout}

CURRENT CODE (`model_part.py`):
{code_str}

Fix the bug in `model_part.py`. Maintain the required signature:
def train_predict(X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series, X_test: Optional[pd.DataFrame] = None) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
Return ONLY the corrected Python code inside ```python ... ```.
"""
            fix_resp = await asyncio.to_thread(query_llm, fix_prompt, system="You are the ML Engineer. Fix the code precisely.")
            m_fix = re.search(r"```(?:python)?\s*\n(.*?)\n```", fix_resp, re.DOTALL)
            code_str = m_fix.group(1) if m_fix else fix_resp

            with open(model_module_path, "w", encoding="utf-8") as f:
                f.write(code_str)
            with open(exp_module_path, "w", encoding="utf-8") as f:
                f.write(code_str)

            self.state["debug_attempts"].append({
                "exp_no": exp_no,
                "attempt": debug_attempts,
                "error": err_msg[:500],
                "fix_summary": f"Refactored model_part.py ({len(code_str)} bytes)",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            self.append_transcript(
                agent="Engineer",
                role="Engineer",
                message=f"Applied Debug Fix #{debug_attempts}/2 for Exp #{exp_no} after error: {err_msg[:120]}"
            )

            exec_res = await self.runner.execute_script(scaffold_dst, args=cmd_args, verify_oof=True, oof_file=oof_file)
            exec_status = exec_res.get("status", "FAILED")
            cv_score = exec_res.get("cv_score")
            fold_scores = exec_res.get("fold_scores", {})

        phase_timings["runner_seconds"] = round(asyncio.get_event_loop().time() - runner_start, 2)
        elapsed_total = asyncio.get_event_loop().time() - exp_start_time
        exit_code = exec_res.get("exit_code")
        signal = exec_res.get("signal")

        # Provenance: Compute SHA-256 hashes and Git commit
        def _calc_sha(path: Path) -> Optional[str]:
            if not path.is_file():
                return None
            h = hashlib.sha256()
            with open(path, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            return h.hexdigest()

        script_sha = _calc_sha(exp_module_path) or _calc_sha(model_module_path)
        oof_sha = _calc_sha(oof_file)
        sub_file = self.run_dir / f"submission_exp{exp_no}.csv"
        sub_sha = _calc_sha(sub_file)

        git_commit = None
        try:
            import subprocess
            git_commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
        except Exception:
            pass

        # Paired fold evaluation vs Exp 0 baseline
        from src.services.kaggle2.evaluator import compute_paired_verdict
        exp0_rec = next((e for e in self.state.get("experiments", []) if e.get("exp_no") == 0), None)
        if exp0_rec and "fold_scores" in exp0_rec:
            base_cv = exp0_rec.get("cv_score", 0.94557)
            fs = exp0_rec["fold_scores"]
            base_folds = [fs.get(str(f), fs.get(f, 0.0)) for f in range(5)]
        else:
            base_cv = 0.94557
            base_folds = [0.94313, 0.94721, 0.95028, 0.94641, 0.94134]

        exp_folds = [fold_scores.get(str(f), fold_scores.get(f, 0.0)) for f in range(5)] if fold_scores and len(fold_scores) == 5 else None
        verdict_info = compute_paired_verdict(exp_folds, base_folds) if (exp_folds and base_folds) else None

        if exec_status != "PASSED":
            self.record_failure("EXPERIMENT_EXECUTION_FAILURE", f"Experiment #{exp_no} exited with status {exec_status} (exit {exit_code})", exec_res.get("last_stderr") or exec_res.get("error"))

        self.state["experiments"].append({
            "exp_no": exp_no,
            "hypothesis": (rebut_resp[:160] + "..." if initial_verdict == "BLOCK" and rebut_resp else strat_resp[:160] + "..."),
            "hypothesis_id": prop_dict.get("hypothesis_id", f"EXP{exp_no}_HYPOTHESIS"),
            "skeptic_verdict": final_verdict,
            "deciding_reason": deciding_reason,
            "code": code_str,
            "cv_score": cv_score,
            "fold_scores": fold_scores,
            "verdict_vs_base": verdict_info.get("verdict") if verdict_info else "N/A",
            "paired_diffs": verdict_info.get("paired_diffs") if verdict_info else [],
            "status": exec_status,
            "exit_code": exit_code,
            "signal": signal,
            "debug_attempts": debug_attempts,
            "phase_timings": phase_timings,
            "elapsed_seconds": round(elapsed_total, 2),
            "script_sha256": script_sha,
            "oof_sha256": oof_sha,
            "submission_sha256": sub_sha,
            "git_commit": git_commit,
            "debate_lineage": debate_lineage
        })

        # ── Step 6: Honest Postmortem & Lesson Generation ──
        # Integrity Rule: No record, no lesson!
        if exec_status == "PASSED" and (not oof_sha or not script_sha):
            logger.error(f"[AgentTeam] Exp #{exp_no} passed execution but lacks OOF or script SHA-256 ('No record, no lesson'). Ingestion aborted.")
            self._save_state()
            return {
                "exp_no": exp_no,
                "status": "FAILED_RECORD_INTEGRITY",
                "cv_score": cv_score,
                "elapsed_seconds": round(elapsed_total, 2)
            }

        what_ran = f"run_scaffold.py with model_part_exp{exp_no}.py ({phase_timings['runner_seconds']}s, exit {exit_code})"
        log_excerpt = (exec_res.get("last_stderr") or exec_res.get("last_stdout") or "")[:400]
        if cv_score is not None:
            verdict_desc = verdict_info.get("verdict") if verdict_info else "UNVERIFIED"
            what_worked = f"Scaffold completed 5-fold CV. CV ROC-AUC: {cv_score:.5f} | Verdict vs Exp 0: {verdict_desc}"
            what_failed = "None" if verdict_desc != "WORSE" else f"Underperformed Exp 0 baseline (Mean diff: {verdict_info.get('mean_diff'):+.5f})"
            why_reasoning = f"Harness computed real out-of-fold ROC-AUC {cv_score:.5f} from oof_exp{exp_no}.parquet"
            next_steps = "Compare vs baseline and explore ensembling / further feature engineering"
        else:
            what_worked = "Sandbox execution and error capture succeeded"
            what_failed = f"Execution failed (exit code {exit_code}). Log excerpt: {log_excerpt}"
            why_reasoning = f"Harness-verified CV: NONE. Model script failed after {debug_attempts} debug attempts"
            next_steps = "Address the root error in model_part.py or simplify feature pipeline"

        lesson_record = await self.lesson_service.create_lesson(
            run_id=self.run_id,
            exp_no=exp_no,
            hypothesis=strat_resp,
            methodology=what_ran,
            cv_score=cv_score,
            what_worked=what_worked,
            what_failed=what_failed,
            why_reasoning=why_reasoning,
            next_steps=next_steps,
            status=exec_status,
            fold_scores=fold_scores,
            base_cv_score=base_cv,
            verdict_info=verdict_info,
            script_sha256=script_sha,
            oof_sha256=oof_sha,
            submission_sha256=sub_sha,
            git_commit=git_commit,
            wall_time=phase_timings['runner_seconds'],
            exit_code=exit_code,
            signal=signal
        )
        self.state["lessons"].append(lesson_record)
        self._save_state()

        self.append_transcript(
            agent="Skeptic",
            role="Skeptic",
            message=f"Experiment #{exp_no} evaluated. Status: {exec_status} | Real CV ROC-AUC: {cv_score if cv_score is not None else 'FAILED / NONE'}. Lesson saved and ingested to NotebookLM."
        )

        return {
            "exp_no": exp_no,
            "status": exec_status,
            "cv_score": cv_score,
            "elapsed_seconds": round(elapsed_total, 2),
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
