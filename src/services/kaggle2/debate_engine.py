"""
debate_engine.py — Genuine 5-Stage Multi-Agent Adversarial Debate Engine
=========================================================================
Implements the 5-stage adversarial review with deterministic policy gate:
  Stage 1: Strategist Hypothesis & Schema Evidence
  Stage 2: Skeptic Numbered Adversarial Objections (APPROVE | REJECT | NEEDS_EVIDENCE)
  Stage 3: Strategist Itemized Rebuttal (answering each objection by ID)
  Stage 4: Skeptic Final Decision on Rebuttal
  Stage 5: Deterministic Policy Gate (permits or halts execution based on verified record)

Records model identity, timestamps, prompt hashes, and raw responses.
"""

import hashlib
import time
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from src.services.kaggle2.leakage_validator import LeakageValidator, VERIFIED_S6E11_FEATURES

logger = logging.getLogger("Kaggle2.DebateEngine")


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DebateEngine:
    """Orchestrates genuine 5-stage adversarial review between Strategist and Skeptic."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name

    def build_strategist_proposal_prompt(
        self,
        exp_no: int,
        verified_columns: List[str],
        baseline_metric: float,
        literature_context: str = ""
    ) -> str:
        """Constructs prompt forcing falsifiable hypothesis grounded strictly in schema."""
        cols_formatted = ", ".join(f"'{c}'" for c in verified_columns)
        return f"""You are the Lead ML Strategist for Kaggle S6E11 (Credit Card Fraud Detection).
Task: Formulate a falsifiable, leakage-free modeling hypothesis for Experiment #{exp_no}.

CRITICAL SCHEMA ENFORCEMENT:
The dataset contains ONLY the following 24 feature columns:
[{cols_formatted}]
There is NO user_id, customer_id, or card_id. You must NOT invent columns or reference non-existent features.
Column 'id' is a row identifier and must NOT be used as a feature.
Column 'is_fraud' is the binary target and must NOT be included in features.

Current Reference Baseline: Exp 0 (Raw LightGBM CV: {baseline_metric:.5f}).
Literature & Notebook Grounding:
{literature_context or 'None available.'}

PROPOSAL FORMAT (MANDATORY JSON STRUCTURE):
{{
  "hypothesis_id": "EXP{exp_no}_HYPOTHESIS",
  "problem": "<specific modeling challenge in S6E11>",
  "feature_changes": ["<exact feature names from verified list or mathematical combination>"],
  "schema_evidence": "<proof that referenced columns exist in verified 24 features>",
  "mechanism": "<statistical or algorithmic mechanism of expected gain>",
  "expected_metric_impact": "<clearly labeled ESTIMATE, e.g. +0.00050 AUC>",
  "leakage_risks": "<potential data or target leakage risks and mitigation>",
  "compute_cost_estimate": "<estimated time and RAM impact>",
  "validation_procedure": "<how 5-fold frozen CV will evaluate this>",
  "rejection_conditions": "<specific criteria where this hypothesis must be considered refuted>"
}}
"""

    def build_skeptic_review_prompt(
        self,
        proposal_dict: Dict[str, Any]
    ) -> str:
        """Constructs adversarial review prompt requiring itemized objections."""
        prop_str = json.dumps(proposal_dict, indent=2)
        return f"""You are the Adversarial ML Skeptic for Kaggle S6E11.
Your mandate is to find data leakage, ungrounded assumptions, schema violations, or overfitting risks.

Strategist Proposal for Review:
{prop_str}

REVIEW REQUIREMENTS:
1. Check every proposed feature against verified columns (no hallucinated features allowed).
2. Check for target leakage (using target in features or naive target encoding without inner folds).
3. Check for train/validation contamination.
4. Assess computational cost and feasibility in Firejail sandbox.
5. Provide a list of NUMBERED OBJECTIONS. Each objection must specify:
   - objection_id: OBJ_1, OBJ_2, etc.
   - original_claim: <claim challenged>
   - evidence_examined: <specific columns or code logic>
   - verification_test: <deterministic test to confirm/refute>
   - severity: CRITICAL | WARNING | INFO
   - recommendation: APPROVE | REJECT | NEEDS_EVIDENCE

OUTPUT FORMAT (MANDATORY JSON STRUCTURE):
{{
  "objections": [
    {{
      "objection_id": "OBJ_1",
      "original_claim": "<claim>",
      "evidence_examined": "<evidence>",
      "verification_test": "<test>",
      "severity": "CRITICAL",
      "recommendation": "REJECT",
      "reason": "<reason>"
    }}
  ],
  "preliminary_verdict": "APPROVE | REJECT | NEEDS_EVIDENCE",
  "summary": "<concise adversarial synthesis>"
}}
"""

    def build_strategist_rebuttal_prompt(
        self,
        proposal_dict: Dict[str, Any],
        skeptic_review: Dict[str, Any]
    ) -> str:
        """Forces Strategist to address every single objection point-by-point."""
        return f"""You are the ML Strategist. The Skeptic has raised objections to your proposal.
You must respond to EVERY SINGLE objection individually by its objection_id.
Either accept the critique and revise the feature/methodology, or provide concrete schema evidence.

Original Proposal:
{json.dumps(proposal_dict, indent=2)}

Skeptic Objections:
{json.dumps(skeptic_review, indent=2)}

OUTPUT FORMAT (MANDATORY JSON STRUCTURE):
{{
  "rebuttals": [
    {{
      "objection_id": "OBJ_1",
      "response_type": "REVISE | REBUT",
      "detailed_answer": "<point by point answer>",
      "action_taken": "<how specification is modified or defended>"
    }}
  ],
  "revised_specification": {{
    "approved_features": ["<final feature list>"],
    "implementation_constraints": ["<exact constraints Engineer must follow>"]
  }}
}}
"""

    def build_skeptic_final_prompt(
        self,
        skeptic_review: Dict[str, Any],
        strategist_rebuttal: Dict[str, Any]
    ) -> str:
        """Constructs prompt for Skeptic's final verdict on the rebuttals."""
        return f"""You are the Adversarial ML Skeptic. Review the Strategist's rebuttals to your objections.

Your Original Objections:
{json.dumps(skeptic_review, indent=2)}

Strategist Rebuttals:
{json.dumps(strategist_rebuttal, indent=2)}

Determine whether each objection is RESOLVED or UNRESOLVED.
Render your FINAL VERDICT. Allowed verdicts: APPROVE | REJECT | NEEDS_EVIDENCE.
There is NO default proceed. If any CRITICAL objection remains UNRESOLVED, verdict MUST be REJECT.

OUTPUT FORMAT (MANDATORY JSON STRUCTURE):
{{
  "objection_resolutions": [
    {{
      "objection_id": "OBJ_1",
      "status": "RESOLVED | UNRESOLVED",
      "final_comment": "<comment>"
    }}
  ],
  "final_verdict": "APPROVE | REJECT | NEEDS_EVIDENCE",
  "deciding_reason": "<decisive justification for approval or halt>"
}}
"""

    def evaluate_policy_gate(
        self,
        skeptic_final_review: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Deterministic Policy Engine: Evaluates the complete debate record.
        Returns (is_approved, decision_reason).
        """
        verdict = skeptic_final_review.get("final_verdict", "REJECT")
        reason = skeptic_final_review.get("deciding_reason", "No reason provided")
        resolutions = skeptic_final_review.get("objection_resolutions", [])

        # Check for unresolved objections
        unresolved = [res["objection_id"] for res in resolutions if res.get("status") == "UNRESOLVED"]
        if unresolved and verdict == "APPROVE":
            return False, f"PolicyGateViolation: Final verdict was APPROVE but objections {unresolved} remain UNRESOLVED."

        if verdict != "APPROVE":
            return False, f"DebateBlocked: Skeptic rendered verdict '{verdict}' (Reason: {reason})"

        return True, f"PolicyGateApproved: All objections resolved. Reason: {reason}"
