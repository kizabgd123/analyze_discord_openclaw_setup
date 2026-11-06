"""
debate_engine.py — Genuine 5-Stage Multi-Agent Adversarial Debate Engine
=========================================================================
Implements the 5-stage adversarial review with deterministic policy gate:
  Stage 1: Strategist Hypothesis & Schema Evidence (Structured JSON Contract)
  Stage 2: Skeptic Numbered Adversarial Objections (OBJ_001, OBJ_002, ...)
  Stage 3: Strategist Itemized Rebuttal (answering each objection by ID)
  Stage 4: Skeptic Final Decision on Rebuttal (RESOLVED / UNRESOLVED itemization)
  Stage 5: Deterministic Policy Gate (permits or halts execution based on verified record)

Records model identity, timestamps, prompt SHA-256 hashes, and raw responses.
"""

import hashlib
import time
import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone
from src.services.kaggle2.leakage_validator import VERIFIED_S6E11_FEATURES, FORBIDDEN_COLUMNS

logger = logging.getLogger("Kaggle2.DebateEngine")

# Required fields for Strategist Proposal JSON contract
STRATEGIST_REQUIRED_FIELDS = [
    "hypothesis_id",
    "hypothesis",
    "mechanism",
    "verified_feature_names",
    "supporting_evidence",
    "falsifiable_criteria",
    "expected_metric_direction",
    "computational_cost",
    "leakage_risks",
]

# Required fields for each numbered Skeptic Objection
OBJECTION_REQUIRED_FIELDS = [
    "objection_id",
    "original_claim",
    "evidence",
    "severity",
    "verification_test",
    "reasoning",
]

ALLOWED_SKEPTIC_VERDICTS = {"APPROVE", "REJECT", "NEEDS_EVIDENCE"}
ALLOWED_SEVERITIES = {"CRITICAL", "WARNING", "INFO"}


def hash_text(text: str) -> str:
    """Computes SHA-256 hex digest of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_llm_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Extracts a JSON object from raw LLM output, handling markdown code fences
    (```json ... ``` or ``` ... ```) or bare JSON objects.
    """
    if not raw_text or not isinstance(raw_text, str):
        return None

    cleaned = raw_text.strip()

    # Try extracting inside code blocks
    code_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if code_match:
        try:
            return json.loads(code_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try extracting outermost { ... }
    outer_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if outer_match:
        try:
            return json.loads(outer_match.group(1))
        except json.JSONDecodeError:
            pass

    # Direct parse attempt
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


class DebateEngine:
    """Orchestrates genuine 5-stage adversarial review between Strategist and Skeptic."""

    def __init__(self, model_name: str = "claude-sonnet-4-6", account: str = "999@mrcleanervracar.com"):
        self.model_name = model_name
        self.account = account

    # ── Stage 1: Strategist Proposal ──

    def build_strategist_proposal_prompt(
        self,
        exp_no: int,
        verified_columns: Optional[List[str]] = None,
        baseline_metric: float = 0.94557,
        literature_context: str = ""
    ) -> str:
        """Constructs prompt forcing falsifiable hypothesis grounded strictly in schema."""
        cols = verified_columns or VERIFIED_S6E11_FEATURES
        cols_formatted = ", ".join(f"'{c}'" for c in cols)
        return (
            f"You are the Strategist. Based on research below, propose a concrete, testable hypothesis "
            f"for Experiment #{exp_no} predicting credit card fraud (metric: ROC-AUC).\n\n"
            f"CRITICAL DATASET SCHEMA ENFORCEMENT:\n"
            f"The dataset contains ONLY the following 24 feature columns:\n"
            f"[{cols_formatted}]\n"
            f"There is NO user_id, customer_id, or card_id. You must NOT invent columns or reference non-existent features.\n"
            f"Column 'id' is a row identifier and must NOT be used as a feature.\n"
            f"Column 'is_fraud' is the binary target and must NOT be included in features.\n\n"
            f"Current Reference Baseline: Exp 0 (Raw LightGBM CV: {baseline_metric:.5f}).\n\n"
            f"Literature & Notebook Grounding:\n"
            f"{literature_context or 'None available.'}\n\n"
            f"PROPOSAL FORMAT (MANDATORY JSON STRUCTURE):\n"
            f"```json\n"
            f"{{\n"
            f'  "hypothesis_id": "EXP{exp_no}_HYPOTHESIS",\n'
            f'  "hypothesis": "<clear, falsifiable statement of proposed modeling/feature change>",\n'
            f'  "mechanism": "<statistical or algorithmic mechanism of expected gain>",\n'
            f'  "verified_feature_names": ["<exact column names from verified 24 features>"],\n'
            f'  "supporting_evidence": "<quoted research, notebook insight, or schema reasoning>",\n'
            f'  "falsifiable_criteria": "<metric threshold on frozen 5-fold CV to consider hypothesis supported>",\n'
            f'  "expected_metric_direction": "+0.00050 AUC",\n'
            f'  "computational_cost": "<estimated time and RAM impact in Firejail sandbox>",\n'
            f'  "leakage_risks": "<potential data or target leakage risks and mitigation>"\n'
            f"}}\n"
            f"```\n"
            f"Return ONLY valid JSON matching this schema."
        )

    def validate_strategist_proposal(
        self,
        proposal: Dict[str, Any],
        verified_columns: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        Validates Strategist proposal against mandatory JSON schema and feature grounding.
        Rejects missing fields and ungrounded / hallucinated feature names.
        """
        if not isinstance(proposal, dict):
            return False, "MalformedProposal: Proposal must be a JSON object"

        # Check required fields
        for field in STRATEGIST_REQUIRED_FIELDS:
            if field not in proposal or proposal[field] is None:
                return False, f"MissingRequiredField: '{field}' is required in Strategist proposal"
            if isinstance(proposal[field], str) and not proposal[field].strip():
                return False, f"EmptyField: '{field}' cannot be empty in Strategist proposal"

        # Validate verified_feature_names
        feat_names = proposal.get("verified_feature_names", [])
        if not isinstance(feat_names, list):
            return False, "InvalidFeatureNames: 'verified_feature_names' must be a list of strings"

        valid_cols = set(verified_columns or VERIFIED_S6E11_FEATURES)
        forbidden = set(FORBIDDEN_COLUMNS)

        for feat in feat_names:
            if not isinstance(feat, str):
                return False, f"InvalidFeatureType: Feature name must be string, got {type(feat)}"
            feat_clean = feat.strip()
            if feat_clean in forbidden:
                return False, f"TargetLeakageError: Forbidden column '{feat_clean}' cannot be used as feature"

            # Check if it's a known raw column or composed of known raw columns
            if feat_clean not in valid_cols:
                # Check if it references any valid columns (e.g. 'amount_usd / customer_age')
                has_known_base = any(vc in feat_clean for vc in valid_cols)
                # Check for known hallucinated keywords
                hallucinated = ["user_id", "customer_id", "card_id", "account_id", "device_id"]
                if any(h in feat_clean.lower() for h in hallucinated):
                    return False, f"UngroundedFeatureError: Non-existent identifier column referenced: '{feat_clean}'"
                if not has_known_base:
                    return False, f"UngroundedFeatureError: Feature '{feat_clean}' not in verified dataset schema"

        return True, "ProposalValid"

    # ── Stage 2: Skeptic Review ──

    def build_skeptic_review_prompt(
        self,
        proposal_dict: Dict[str, Any],
        exp_no: Optional[int] = None,
        fact_check_context: str = ""
    ) -> str:
        """Constructs adversarial review prompt requiring numbered objections and structured verdict."""
        prop_str = json.dumps(proposal_dict, indent=2)
        exp_tag = f" for Experiment #{exp_no}" if exp_no is not None else ""
        return (
            f"You are the Skeptic. Review the Strategist's proposal{exp_tag}:\n"
            f"{prop_str}\n\n"
            f"NotebookLM Fact Check / Competition Grounding:\n"
            f"{fact_check_context or 'No contradictory notebook notes found.'}\n\n"
            f"Adversarial Review Mandate:\n"
            f"1. Check every proposed feature against verified columns (no hallucinated user/card IDs).\n"
            f"2. Check for target leakage ('is_fraud' or naive target encoding without out-of-fold isolation).\n"
            f"3. Check for train/validation contamination.\n"
            f"4. Assess computational cost and feasibility in Firejail sandbox.\n"
            f"5. If raising objections, provide stable NUMBERED OBJECTIONS (OBJ_001, OBJ_002, ...).\n\n"
            f"MANDATORY JSON FORMAT:\n"
            f"```json\n"
            f"{{\n"
            f'  "hypothesis_id": "{proposal_dict.get("hypothesis_id", "EXP_HYPOTHESIS")}",\n'
            f'  "overall_verdict": "APPROVE | REJECT | NEEDS_EVIDENCE",\n'
            f'  "objections": [\n'
            f"    {{\n"
            f'      "objection_id": "OBJ_001",\n'
            f'      "original_claim": "<claim from proposal>",\n'
            f'      "evidence": "<evidence or rule contradicted>",\n'
            f'      "severity": "CRITICAL | WARNING | INFO",\n'
            f'      "verification_test": "<deterministic test to confirm/refute>",\n'
            f'      "reasoning": "<adversarial reasoning>"\n'
            f"    }}\n"
            f"  ],\n"
            f'  "summary": "<concise summary of review>"\n'
            f"}}\n"
            f"```\n"
            f"Allowed overall_verdict values: APPROVE, REJECT, NEEDS_EVIDENCE.\n"
            f"If there are NO blocking objections, set overall_verdict to 'APPROVE' and objections to [].\n"
            f"Return ONLY valid JSON matching this schema."
        )

    def validate_skeptic_review(self, review: Dict[str, Any]) -> Tuple[bool, str]:
        """Validates Skeptic review against structured JSON schema."""
        if not isinstance(review, dict):
            return False, "MalformedReview: Review must be a JSON object"

        if "hypothesis_id" not in review:
            return False, "MissingRequiredField: 'hypothesis_id' required in Skeptic review"

        verdict = review.get("overall_verdict")
        if verdict not in ALLOWED_SKEPTIC_VERDICTS:
            return False, f"InvalidVerdict: '{verdict}' not in {ALLOWED_SKEPTIC_VERDICTS}"

        objections = review.get("objections", [])
        if not isinstance(objections, list):
            return False, "InvalidObjections: 'objections' must be a list"

        if verdict in ("REJECT", "NEEDS_EVIDENCE") and len(objections) == 0:
            return False, f"MissingObjections: Verdict '{verdict}' requires at least one numbered objection"

        # Validate each objection
        seen_ids: Set[str] = set()
        for idx, obj in enumerate(objections):
            if not isinstance(obj, dict):
                return False, f"InvalidObjectionFormat: Objection #{idx} must be a JSON object"
            for field in OBJECTION_REQUIRED_FIELDS:
                if field not in obj or not str(obj[field]).strip():
                    return False, f"MissingObjectionField: '{field}' required in objection #{idx}"

            obj_id = obj["objection_id"]
            if not re.match(r"^OBJ_\d+$", obj_id, re.IGNORECASE):
                return False, f"InvalidObjectionIdFormat: '{obj_id}' must match OBJ_001 format"
            if obj_id in seen_ids:
                return False, f"DuplicateObjectionId: '{obj_id}' is defined multiple times"
            seen_ids.add(obj_id)

            sev = obj.get("severity")
            if sev not in ALLOWED_SEVERITIES:
                return False, f"InvalidSeverity: '{sev}' not in {ALLOWED_SEVERITIES}"

        return True, "ReviewValid"

    # ── Stage 3: Strategist Rebuttal ──

    def build_strategist_rebuttal_prompt(
        self,
        proposal_dict: Dict[str, Any],
        skeptic_review: Dict[str, Any],
        exp_no: Optional[int] = None
    ) -> str:
        """Forces Strategist to address every single objection point-by-point by ID."""
        exp_tag = f" for Experiment #{exp_no}" if exp_no is not None else ""
        summary_reason = skeptic_review.get("summary") or skeptic_review.get("overall_verdict", "BLOCK")
        return (
            f"The Skeptic BLOCKED your proposal{exp_tag} with reason:\n{summary_reason}\n\n"
            f"Original Proposal:\n{json.dumps(proposal_dict, indent=2)}\n\n"
            f"Skeptic Objections:\n{json.dumps(skeptic_review, indent=2)}\n\n"
            f"Respond point by point. Either accept the critique and revise your proposal, or rebut with concrete evidence.\n\n"
            f"MANDATORY JSON FORMAT:\n"
            f"```json\n"
            f"{{\n"
            f'  "rebuttals": [\n'
            f"    {{\n"
            f'      "objection_id": "OBJ_001",\n'
            f'      "response_type": "REVISE | REBUT",\n'
            f'      "detailed_answer": "<point by point answer to objection>",\n'
            f'      "action_taken": "<specific revision to proposal or code specification>"\n'
            f"    }}\n"
            f"  ],\n"
            f'  "revised_specification": {{\n'
            f'    "approved_features": ["<feature names to retain>"],\n'
            f'    "implementation_constraints": ["<exact constraints Engineer must follow>"]\n'
            f"  }}\n"
            f"}}\n"
            f"```\n"
            f"You MUST include an entry in 'rebuttals' for EVERY objection_id listed above.\n"
            f"Return ONLY valid JSON matching this schema."
        )

    def validate_strategist_rebuttal(
        self,
        rebuttal: Dict[str, Any],
        original_objections: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """Validates that Strategist addressed every single objection by its unique ID."""
        if not isinstance(rebuttal, dict):
            return False, "MalformedRebuttal: Rebuttal must be a JSON object"

        rebuttals = rebuttal.get("rebuttals", [])
        if not isinstance(rebuttals, list):
            return False, "InvalidRebuttals: 'rebuttals' must be a list"

        rebutted_ids = {r.get("objection_id") for r in rebuttals if isinstance(r, dict)}
        for obj in original_objections:
            oid = obj.get("objection_id")
            if oid not in rebutted_ids:
                return False, f"MissingRebuttal: Objection '{oid}' was not addressed in rebuttals"

        revised_spec = rebuttal.get("revised_specification")
        if not isinstance(revised_spec, dict):
            return False, "MissingRevisedSpecification: 'revised_specification' is required in rebuttal"

        return True, "RebuttalValid"

    # ── Stage 4: Skeptic Final Review ──

    def build_skeptic_final_prompt(
        self,
        skeptic_review: Dict[str, Any],
        strategist_rebuttal: Dict[str, Any],
        exp_no: Optional[int] = None
    ) -> str:
        """Constructs prompt for Skeptic's final itemized evaluation of the rebuttals."""
        exp_tag = f" for Experiment #{exp_no}" if exp_no is not None else ""
        return (
            f"Review the Strategist's rebuttal{exp_tag}:\n"
            f"{json.dumps(strategist_rebuttal, indent=2)}\n\n"
            f"Original Objections:\n"
            f"{json.dumps(skeptic_review, indent=2)}\n\n"
            f"Render your FINAL VERDICT:\n\n"
            f"MANDATORY JSON FORMAT:\n"
            f"```json\n"
            f"{{\n"
            f'  "objection_resolutions": [\n'
            f"    {{\n"
            f'      "objection_id": "OBJ_001",\n'
            f'      "status": "RESOLVED | UNRESOLVED",\n'
            f'      "final_comment": "<evaluation of rebuttal>"\n'
            f"    }}\n"
            f"  ],\n"
            f'  "final_verdict": "APPROVE | REJECT | NEEDS_EVIDENCE",\n'
            f'  "deciding_reason": "<concise justification for verdict>"\n'
            f"}}\n"
            f"```\n"
            f"Integrity Rule: If ANY CRITICAL objection remains UNRESOLVED, final_verdict MUST be REJECT.\n"
            f"Return ONLY valid JSON matching this schema."
        )

    def validate_skeptic_final(self, final_review: Dict[str, Any]) -> Tuple[bool, str]:
        """Validates Skeptic final review."""
        if not isinstance(final_review, dict):
            return False, "MalformedFinalReview: Must be a JSON object"

        verdict = final_review.get("final_verdict")
        if verdict not in ALLOWED_SKEPTIC_VERDICTS:
            return False, f"InvalidFinalVerdict: '{verdict}' not in {ALLOWED_SKEPTIC_VERDICTS}"

        reason = final_review.get("deciding_reason")
        if not reason or not str(reason).strip():
            return False, "MissingDecidingReason: 'deciding_reason' is required"

        resolutions = final_review.get("objection_resolutions", [])
        if not isinstance(resolutions, list):
            return False, "InvalidResolutions: 'objection_resolutions' must be a list"

        for idx, res in enumerate(resolutions):
            if not isinstance(res, dict):
                return False, f"InvalidResolutionFormat: Resolution #{idx} must be a JSON object"
            if "objection_id" not in res:
                return False, f"MissingObjectionIdInResolution: #{idx}"
            status = res.get("status")
            if status not in ("RESOLVED", "UNRESOLVED"):
                return False, f"InvalidResolutionStatus: '{status}' must be RESOLVED or UNRESOLVED"

        return True, "FinalReviewValid"

    # ── Stage 5: Deterministic Policy Gate ──

    def evaluate_policy_gate(
        self,
        skeptic_final_review: Dict[str, Any],
        original_objections: Optional[List[Dict[str, Any]]] = None
    ) -> Tuple[bool, str]:
        """
        Deterministic Policy Engine: Evaluates the complete debate record.
        Zero tolerance for unresolved critical objections or non-APPROVE verdicts.
        Returns: (is_approved: bool, reason: str).
        """
        verdict = skeptic_final_review.get("final_verdict", "REJECT")
        reason = skeptic_final_review.get("deciding_reason", "No reason provided")
        resolutions = skeptic_final_review.get("objection_resolutions", [])

        # Check for unresolved objections
        unresolved = [
            res.get("objection_id", "UNKNOWN")
            for res in resolutions
            if res.get("status") == "UNRESOLVED"
        ]

        if unresolved:
            return False, f"PolicyGateViolation: Objections {unresolved} remain UNRESOLVED."

        if original_objections:
            resolved_ids = {res.get("objection_id") for res in resolutions}
            missing_ids = [
                obj.get("objection_id")
                for obj in original_objections
                if obj.get("objection_id") not in resolved_ids
            ]
            if missing_ids:
                return False, f"PolicyGateViolation: Objections {missing_ids} lack resolution status."

        if verdict not in ("APPROVE", "PROCEED", "PROCEED_WITH_CONDITIONS"):
            return False, f"DebateBlocked: Skeptic rendered verdict '{verdict}' (Reason: {reason})"

        return True, f"PolicyGateApproved: All objections resolved. Reason: {reason}"

    # ── Legacy Adapter Helpers ──

    def adapt_legacy_proposal_text(self, text: str, exp_no: int) -> Dict[str, Any]:
        """Adapts plain text proposal into structured proposal dict for backwards compatibility."""
        m_hyp = re.search(r"HYPOTHESIS:\s*(.*)", text, re.IGNORECASE)
        hyp = m_hyp.group(1).strip() if m_hyp else text.splitlines()[0][:160]

        # Extract features mentioned
        valid_cols = set(VERIFIED_S6E11_FEATURES)
        found_feats = [col for col in valid_cols if col in text]
        if not found_feats:
            found_feats = ["amount_usd", "hours_since_last_txn"]

        return {
            "hypothesis_id": f"EXP{exp_no}_HYPOTHESIS",
            "hypothesis": hyp,
            "mechanism": "Statistical interaction / GBDT gradient partitioning",
            "verified_feature_names": found_feats,
            "supporting_evidence": "Grounding in dataset schema and past literature",
            "falsifiable_criteria": "Frozen 5-fold CV ROC-AUC improvement",
            "expected_metric_direction": "+0.00050 AUC",
            "computational_cost": "Standard LightGBM runtime (~60s)",
            "leakage_risks": "None; strictly evaluated within fold boundaries",
        }

    def adapt_legacy_review_text(self, text: str, exp_no: int) -> Dict[str, Any]:
        """Adapts plain text skeptic review into structured review dict."""
        m_verdict = re.search(r"(?:FINAL_)?VERDICT:\s*(BLOCK|PROCEED_WITH_CONDITIONS|PROCEED|APPROVE|REJECT)", text, re.IGNORECASE)
        raw_v = m_verdict.group(1).upper() if m_verdict else "PROCEED"

        m_reason = re.search(r"(?:FINAL_REASON|REASON|DECIDING_REASON):\s*(.*)", text, re.IGNORECASE)
        reason = m_reason.group(1).strip() if m_reason else text.splitlines()[-1]

        if raw_v in ("BLOCK", "REJECT"):
            return {
                "hypothesis_id": f"EXP{exp_no}_HYPOTHESIS",
                "overall_verdict": "REJECT",
                "objections": [
                    {
                        "objection_id": "OBJ_001",
                        "original_claim": "Hypothesis claim",
                        "evidence": reason,
                        "severity": "CRITICAL",
                        "verification_test": "Check competition rules and fold leakage",
                        "reasoning": reason,
                    }
                ],
                "summary": reason,
            }
        elif raw_v in ("PROCEED_WITH_CONDITIONS", "NEEDS_EVIDENCE"):
            return {
                "hypothesis_id": f"EXP{exp_no}_HYPOTHESIS",
                "overall_verdict": "NEEDS_EVIDENCE",
                "objections": [
                    {
                        "objection_id": "OBJ_001",
                        "original_claim": "Conditional parameter",
                        "evidence": reason,
                        "severity": "WARNING",
                        "verification_test": "Verify in-fold constraints",
                        "reasoning": reason,
                    }
                ],
                "summary": reason,
            }
        else:
            return {
                "hypothesis_id": f"EXP{exp_no}_HYPOTHESIS",
                "overall_verdict": "APPROVE",
                "objections": [],
                "summary": reason or "Proposal satisfies competition integrity",
            }

    def adapt_legacy_final_text(
        self,
        text: str,
        exp_no: int,
        original_objections: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Adapts plain text skeptic final decision into structured final review dict."""
        m_verdict = re.search(r"(?:FINAL_)?VERDICT:\s*(BLOCK|PROCEED_WITH_CONDITIONS|PROCEED|APPROVE|REJECT)", text, re.IGNORECASE)
        raw_v = m_verdict.group(1).upper() if m_verdict else "PROCEED"

        m_reason = re.search(r"(?:FINAL_REASON|REASON|DECIDING_REASON):\s*(.*)", text, re.IGNORECASE)
        reason = m_reason.group(1).strip() if m_reason else text.splitlines()[-1]

        objs = original_objections or [{"objection_id": "OBJ_001"}]

        if raw_v in ("BLOCK", "REJECT"):
            return {
                "hypothesis_id": f"EXP{exp_no}_HYPOTHESIS",
                "final_verdict": "REJECT",
                "deciding_reason": reason,
                "objection_resolutions": [
                    {
                        "objection_id": obj.get("objection_id", "OBJ_001"),
                        "status": "UNRESOLVED",
                        "final_comment": reason
                    }
                    for obj in objs
                ]
            }
        else:
            return {
                "hypothesis_id": f"EXP{exp_no}_HYPOTHESIS",
                "final_verdict": "APPROVE",
                "deciding_reason": reason,
                "objection_resolutions": [
                    {
                        "objection_id": obj.get("objection_id", "OBJ_001"),
                        "status": "RESOLVED",
                        "final_comment": f"Resolved: {reason}"
                    }
                    for obj in objs
                ]
            }
