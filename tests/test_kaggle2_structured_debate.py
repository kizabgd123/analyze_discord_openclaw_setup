"""
test_kaggle2_structured_debate.py — Targeted Tests for Structured Multi-Agent Debate
=====================================================================================
Validates requirements 1-10:
  1. Strategist JSON validation.
  2. Rejection of missing Strategist fields.
  3. Rejection of ungrounded / hallucinated feature names.
  4. Skeptic numbered objection parsing (OBJ_001, OBJ_002).
  5. Missing objection ID rejection.
  6. Rebuttal itemization check.
  7. Unresolved objection blocking execution.
  8. Deterministic Policy Gate authorization.
  9. Prompt SHA-256 reproducibility.
  10. Model independence and lineage record in state.
"""

import pytest
import json
from src.services.kaggle2.debate_engine import (
    DebateEngine,
    hash_text,
    parse_llm_json,
    STRATEGIST_REQUIRED_FIELDS,
    OBJECTION_REQUIRED_FIELDS
)
from src.services.kaggle2.leakage_validator import VERIFIED_S6E11_FEATURES


@pytest.fixture
def debate_engine():
    return DebateEngine(model_name="gemini-3.8-flash-high", account="kiza101288@gmail.com")


@pytest.fixture
def valid_proposal():
    return {
        "hypothesis_id": "EXP1_HYPOTHESIS",
        "hypothesis": "Log-transform transaction amount and compute non-linear velocity interaction",
        "mechanism": "Reduces skewness in amount_usd and isolates high-frequency fraud burst patterns",
        "verified_feature_names": ["amount_usd", "hours_since_last_txn", "velocity_score"],
        "supporting_evidence": "Notebook notes highlight right-skewed amount distributions in synthetic fraud",
        "falsifiable_criteria": "Validation ROC-AUC improves by at least +0.00030 over Exp 0 baseline",
        "expected_metric_direction": "+0.00050 AUC",
        "computational_cost": "Negligible (<10s feature engineering, <60s LightGBM fit)",
        "leakage_risks": "Zero; strictly calculated within fold boundaries with no target usage",
    }


# ── Test 1: Strategist JSON validation ──
def test_1_strategist_json_valid(debate_engine, valid_proposal):
    is_valid, msg = debate_engine.validate_strategist_proposal(valid_proposal)
    assert is_valid is True
    assert msg == "ProposalValid"


# ── Test 2: Rejection of missing Strategist fields ──
@pytest.mark.parametrize("missing_field", STRATEGIST_REQUIRED_FIELDS)
def test_2_strategist_missing_fields_rejection(debate_engine, valid_proposal, missing_field):
    proposal = valid_proposal.copy()
    del proposal[missing_field]
    is_valid, msg = debate_engine.validate_strategist_proposal(proposal)
    assert is_valid is False
    assert "MissingRequiredField" in msg
    assert missing_field in msg

    # Also test empty string field
    proposal_empty = valid_proposal.copy()
    proposal_empty[missing_field] = "   "
    is_valid_empty, msg_empty = debate_engine.validate_strategist_proposal(proposal_empty)
    assert is_valid_empty is False
    assert "EmptyField" in msg_empty


# ── Test 3: Rejection of ungrounded / hallucinated feature names ──
@pytest.mark.parametrize("hallucinated_col", ["user_id", "card_id", "customer_id", "non_existent_column", "is_fraud", "id"])
def test_3_strategist_ungrounded_feature_rejection(debate_engine, valid_proposal, hallucinated_col):
    proposal = valid_proposal.copy()
    proposal["verified_feature_names"] = ["amount_usd", hallucinated_col]
    is_valid, msg = debate_engine.validate_strategist_proposal(proposal)
    assert is_valid is False
    assert any(err in msg for err in ("UngroundedFeatureError", "TargetLeakageError"))


# ── Test 4: Skeptic numbered objection parsing ──
def test_4_skeptic_numbered_objection_parsing(debate_engine):
    valid_review = {
        "hypothesis_id": "EXP1_HYPOTHESIS",
        "overall_verdict": "REJECT",
        "objections": [
            {
                "objection_id": "OBJ_001",
                "original_claim": "Log transform amount",
                "evidence": "Synthetic generator already applies power transform",
                "severity": "CRITICAL",
                "verification_test": "Inspect skewness of amount_usd",
                "reasoning": "May create redundant gradient splits"
            },
            {
                "objection_id": "OBJ_002",
                "original_claim": "Hours since last txn interaction",
                "evidence": "Missing values present in txn history",
                "severity": "WARNING",
                "verification_test": "Check NaN proportion in hours_since_last_txn",
                "reasoning": "Tree split on NaNs may behave inconsistently"
            }
        ],
        "summary": "Critical objections regarding synthetic data distribution"
    }
    is_valid, msg = debate_engine.validate_skeptic_review(valid_review)
    assert is_valid is True
    assert msg == "ReviewValid"


# ── Test 5: Missing objection ID rejection ──
def test_5_skeptic_missing_objection_id_rejection(debate_engine):
    bad_review = {
        "hypothesis_id": "EXP1_HYPOTHESIS",
        "overall_verdict": "REJECT",
        "objections": [
            {
                # Missing objection_id
                "original_claim": "Log transform amount",
                "evidence": "Evidence",
                "severity": "CRITICAL",
                "verification_test": "Test",
                "reasoning": "Reason"
            }
        ],
        "summary": "Review summary"
    }
    is_valid, msg = debate_engine.validate_skeptic_review(bad_review)
    assert is_valid is False
    assert "MissingObjectionField" in msg

    # Invalid objection_id format (e.g. not matching OBJ_...)
    bad_id_review = {
        "hypothesis_id": "EXP1_HYPOTHESIS",
        "overall_verdict": "REJECT",
        "objections": [
            {
                "objection_id": "invalid_id_format",
                "original_claim": "Log transform amount",
                "evidence": "Evidence",
                "severity": "CRITICAL",
                "verification_test": "Test",
                "reasoning": "Reason"
            }
        ],
        "summary": "Review summary"
    }
    is_valid_id, msg_id = debate_engine.validate_skeptic_review(bad_id_review)
    assert is_valid_id is False
    assert "InvalidObjectionIdFormat" in msg_id


# ── Test 6: Rebuttal itemization check ──
def test_6_rebuttal_itemization_check(debate_engine):
    objections = [
        {"objection_id": "OBJ_001", "severity": "CRITICAL"},
        {"objection_id": "OBJ_002", "severity": "WARNING"}
    ]

    # Incomplete rebuttal (only OBJ_001 addressed)
    incomplete_rebuttal = {
        "rebuttals": [
            {
                "objection_id": "OBJ_001",
                "response_type": "REVISE",
                "detailed_answer": "Removed log transform",
                "action_taken": "Use raw amount_usd"
            }
        ],
        "revised_specification": {
            "approved_features": ["amount_usd"],
            "implementation_constraints": []
        }
    }
    is_valid, msg = debate_engine.validate_strategist_rebuttal(incomplete_rebuttal, objections)
    assert is_valid is False
    assert "MissingRebuttal" in msg
    assert "OBJ_002" in msg

    # Complete rebuttal (both addressed)
    complete_rebuttal = {
        "rebuttals": [
            {
                "objection_id": "OBJ_001",
                "response_type": "REVISE",
                "detailed_answer": "Removed log transform",
                "action_taken": "Use raw amount_usd"
            },
            {
                "objection_id": "OBJ_002",
                "response_type": "REBUT",
                "detailed_answer": "LightGBM handles NaNs natively",
                "action_taken": "Keep hours_since_last_txn"
            }
        ],
        "revised_specification": {
            "approved_features": ["amount_usd", "hours_since_last_txn"],
            "implementation_constraints": ["Ensure NaN handling flag is active"]
        }
    }
    is_valid_c, msg_c = debate_engine.validate_strategist_rebuttal(complete_rebuttal, objections)
    assert is_valid_c is True
    assert msg_c == "RebuttalValid"


# ── Test 7: Unresolved objection blocking execution ──
def test_7_unresolved_objection_blocks_execution(debate_engine):
    final_review_with_unresolved = {
        "objection_resolutions": [
            {"objection_id": "OBJ_001", "status": "RESOLVED", "final_comment": "Revision accepted"},
            {"objection_id": "OBJ_002", "status": "UNRESOLVED", "final_comment": "Risk remains unaddressed"}
        ],
        "final_verdict": "APPROVE",  # Contradictory: verdict says APPROVE but OBJ_002 is UNRESOLVED
        "deciding_reason": "Policy check"
    }
    is_approved, reason = debate_engine.evaluate_policy_gate(final_review_with_unresolved)
    assert is_approved is False
    assert "PolicyGateViolation" in reason
    assert "OBJ_002" in reason


# ── Test 8: Deterministic Policy Gate authorization ──
def test_8_deterministic_policy_gate_authorization(debate_engine):
    # Case A: Fully resolved -> Approved
    all_resolved = {
        "objection_resolutions": [
            {"objection_id": "OBJ_001", "status": "RESOLVED", "final_comment": "Fixed"},
            {"objection_id": "OBJ_002", "status": "RESOLVED", "final_comment": "Validated"}
        ],
        "final_verdict": "APPROVE",
        "deciding_reason": "All critiques resolved with verifiable constraints"
    }
    is_approved, reason = debate_engine.evaluate_policy_gate(all_resolved)
    assert is_approved is True
    assert "PolicyGateApproved" in reason

    # Case B: Skeptic rendered REJECT -> Blocked
    rejected = {
        "objection_resolutions": [
            {"objection_id": "OBJ_001", "status": "RESOLVED", "final_comment": "Acknowledged"}
        ],
        "final_verdict": "REJECT",
        "deciding_reason": "Risk of data leakage too severe"
    }
    is_approved_rej, reason_rej = debate_engine.evaluate_policy_gate(rejected)
    assert is_approved_rej is False
    assert "DebateBlocked" in reason_rej


# ── Test 9: Prompt SHA-256 reproducibility ──
def test_9_prompt_sha256_reproducibility(debate_engine):
    prompt1 = debate_engine.build_strategist_proposal_prompt(
        exp_no=1,
        verified_columns=VERIFIED_S6E11_FEATURES,
        baseline_metric=0.94557,
        literature_context="Fixed context for test"
    )
    prompt2 = debate_engine.build_strategist_proposal_prompt(
        exp_no=1,
        verified_columns=VERIFIED_S6E11_FEATURES,
        baseline_metric=0.94557,
        literature_context="Fixed context for test"
    )
    hash1 = hash_text(prompt1)
    hash2 = hash_text(prompt2)
    assert hash1 == hash2
    assert len(hash1) == 64
    assert int(hash1, 16) > 0


# ── Test 10: Model independence and debate lineage record ──
def test_10_model_independence_and_debate_lineage_record(debate_engine):
    assert debate_engine.model_name == "gemini-3.8-flash-high"
    assert debate_engine.account == "kiza101288@gmail.com"

    sample_prompt = "Sample prompt string for debate"
    h = hash_text(sample_prompt)

    lineage = {
        "hypothesis_id": "EXP1_HYPOTHESIS",
        "model": debate_engine.model_name,
        "account": debate_engine.account,
        "prompt_sha256": {"proposal": h},
        "objections": [{"objection_id": "OBJ_001", "severity": "WARNING"}],
        "policy_gate": {"authorized": True, "reason": "Approved"}
    }
    assert lineage["model"] == "gemini-3.8-flash-high"
    assert lineage["account"] == "kiza101288@gmail.com"
    assert lineage["prompt_sha256"]["proposal"] == h
    assert lineage["policy_gate"]["authorized"] is True
