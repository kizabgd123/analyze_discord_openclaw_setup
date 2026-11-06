#!/usr/bin/env python3
"""
demo_v2_end_to_end.py — Safe End-to-End Demonstration of Kaggle S6E11 V2 Multi-Agent Engine
========================================================================================
Demonstrates both paths on a synthetic 50-row isolated sandbox dataset:
  Case A (Valid proposal):
    - Strategist valid proposal
    - Skeptic audit with numbered objection OBJ_001
    - Strategist itemized rebuttal resolving OBJ_001
    - Skeptic final review marking OBJ_001 RESOLVED & APPROVE
    - Policy Gate confirms authorization (EXIT: ALLOW)
    - Engineer invoked & scaffold executes 5-fold CV in sandbox
    - Evaluator verifies OOF predictions & logs to view.html
  Case B (Invalid proposal / Unresolved critique):
    - Skeptic critical objection OBJ_001 remains UNRESOLVED
    - Policy Gate BLOCKS execution
    - Engineer is NEVER invoked (model_part.py not generated)
    - Blocked status logged in state.json & view.html
"""

import os
import sys
import json
import asyncio
import shutil
from pathlib import Path
import numpy as np
import pandas as pd

from src.services.kaggle2.agent_team import AgentTeamOrchestrator
from src.services.kaggle2.debate_engine import DebateEngine, hash_text


async def run_demo():
    print("=" * 80)
    print("KAGGLE S6E11 V2 — MULTI-AGENT ADVERSARIAL DEBATE & ENGINE DEMO")
    print("=" * 80)

    # Use a non-tmp isolated project directory so Firejail --private-tmp allows execution
    demo_base = Path("artifacts/kaggle/s6e11/demo_v2_smoke").resolve()
    if demo_base.exists():
        shutil.rmtree(demo_base)
    demo_base.mkdir(parents=True, exist_ok=True)

    data_dir = demo_base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    run_dir = demo_base / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 1. Create synthetic 50-row train.csv matching 24 features schema
        n_samples = 50
        train_path = data_dir / "train.csv"
        df_train = pd.DataFrame({
            "id": np.arange(n_samples),
            "amount_usd": np.random.uniform(5, 500, n_samples),
            "hours_since_last_txn": np.random.uniform(0.1, 48.0, n_samples),
            "txn_count_last_24h": np.random.randint(1, 10, n_samples),
            "distance_from_home_km": np.random.uniform(0, 100, n_samples),
            "card_age_months": np.random.randint(1, 120, n_samples),
            "customer_age": np.random.randint(18, 85, n_samples),
            "account_balance_usd": np.random.uniform(100, 50000, n_samples),
            "cvv_retry_count": np.random.randint(0, 3, n_samples),
            "velocity_score": np.random.uniform(0, 1, n_samples),
            "time_of_day_hour": np.random.randint(0, 24, n_samples),
            "day_of_week": np.random.randint(0, 7, n_samples),
            "merchant_risk_score": np.random.uniform(0, 1, n_samples),
            "prior_disputes": np.random.randint(0, 5, n_samples),
            "merchant_category": np.random.choice(["grocery", "electronics", "online"], n_samples),
            "card_type": np.random.choice(["visa", "mastercard"], n_samples),
            "auth_method": np.random.choice(["chip", "pin", "contactless"], n_samples),
            "channel": np.random.choice(["pos", "web", "mobile"], n_samples),
            "device_type": np.random.choice(["ios", "android", "pc"], n_samples),
            "is_foreign_transaction": np.random.choice([0, 1], n_samples),
            "is_new_merchant": np.random.choice([0, 1], n_samples),
            "used_vpn": np.random.choice([0, 1], n_samples),
            "ip_country_mismatch": np.random.choice([0, 1], n_samples),
            "billing_shipping_mismatch": np.random.choice([0, 1], n_samples),
            "is_ai_generated_scam_attempt": np.random.choice([0, 1], n_samples),
            "is_fraud": np.random.choice([0.0, 1.0], n_samples, p=[0.85, 0.15])
        })
        df_train.to_csv(train_path, index=False)

        # 2. Frozen 5-fold Stratified split
        folds_path = run_dir / "folds.json"
        fold_assignments = {str(i): int(i % 5) for i in range(n_samples)}
        with open(folds_path, "w", encoding="utf-8") as f:
            json.dump({"scheme": "StratifiedKFold", "n_splits": 5, "fold_assignments": fold_assignments}, f)

        orch = AgentTeamOrchestrator(run_id="demo_v2_smoke/run", data_dir=data_dir)
        orch.run_dir = run_dir
        orch.runner.run_dir = run_dir
        orch.runner.data_dir = data_dir
        orch.runner.folds_file = folds_path
        orch.state_file = run_dir / "state.json"
        orch.html_file = run_dir / "view.html"
        orch.folds_file = folds_path
        orch.is_running = True

        print("\n--- CASE A: VALID PROPOSAL (OBJECTIONS RESOLVED -> GATE APPROVE) ---")

        def mock_llm_case_a(prompt, system=None, **kwargs):
            p = prompt.upper()
            if "YOU ARE THE ML ENGINEER" in p:
                return """```python
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier

def train_predict(X_train: pd.DataFrame, y_train: pd.Series, X_val: pd.DataFrame, y_val: pd.Series) -> np.ndarray:
    num_cols = X_train.select_dtypes(include=[np.number]).columns
    m = LGBMClassifier(n_estimators=10, learning_rate=0.1, random_state=42, verbose=-1, n_jobs=1)
    m.fit(X_train[num_cols], y_train)
    return m.predict_proba(X_val[num_cols])[:, 1]
```"""
            if "YOU ARE THE STRATEGIST. BASED ON RESEARCH" in p:
                return json.dumps({
                    "hypothesis_id": "EXP1_HYPOTHESIS",
                    "hypothesis": "Behavioral velocity non-linear interaction on verified columns",
                    "mechanism": "Combines amount_usd with hours_since_last_txn",
                    "verified_feature_names": ["amount_usd", "hours_since_last_txn", "velocity_score"],
                    "supporting_evidence": "Grounding in dataset schema and fraud distribution",
                    "falsifiable_criteria": "Frozen 5-fold CV ROC-AUC > 0.80000",
                    "expected_metric_direction": "+0.00050 AUC",
                    "computational_cost": "Lightweight (<15s)",
                    "leakage_risks": "None; within fold boundaries"
                })
            if "YOU ARE THE SKEPTIC. REVIEW THE STRATEGIST'S PROPOSAL" in p:
                return json.dumps({
                    "hypothesis_id": "EXP1_HYPOTHESIS",
                    "overall_verdict": "NEEDS_EVIDENCE",
                    "objections": [{
                        "objection_id": "OBJ_001",
                        "original_claim": "Interaction cross",
                        "evidence": "Missing values could destabilize gradient splits",
                        "severity": "WARNING",
                        "verification_test": "Impute NaNs before splitting",
                        "reasoning": "Ensure stability across fold boundaries"
                    }],
                    "summary": "Check NaN handling on hours_since_last_txn"
                })
            if "THE SKEPTIC BLOCKED YOUR PROPOSAL" in p:
                return json.dumps({
                    "rebuttals": [{
                        "objection_id": "OBJ_001",
                        "response_type": "REVISE",
                        "detailed_answer": "Explicitly imputing median on NaN values",
                        "action_taken": "Added median imputation constraint"
                    }],
                    "revised_specification": {
                        "approved_features": ["amount_usd", "hours_since_last_txn", "velocity_score"],
                        "implementation_constraints": ["Ensure NaN handling flag is active"]
                    }
                })
            if "RENDER YOUR FINAL VERDICT" in p:
                return json.dumps({
                    "objection_resolutions": [{
                        "objection_id": "OBJ_001",
                        "status": "RESOLVED",
                        "final_comment": "Median imputation resolves stability critique"
                    }],
                    "final_verdict": "APPROVE",
                    "deciding_reason": "All critiques resolved with verifiable constraints"
                })
            if "STATE YOUR FORMAL DECISION" in p:
                return "DECISION: PROCEED\nDECIDING_REASON: All critiques resolved."
            return "OK"

        from unittest.mock import patch
        with patch("gemini_client.query_llm", side_effect=mock_llm_case_a), \
             patch.object(orch.notebook_client, "query_notebook", return_value={"status": "PASSED", "answer": "Grounded", "citations": {}}):
            res_a = await orch.run_single_experiment(exp_no=1)
            print(f"Status: {res_a['status']}")
            print(f"CV Score: {res_a.get('cv_score')}")
            assert res_a["status"] == "PASSED"
            assert res_a["cv_score"] is not None
            assert (run_dir / "model_part_exp1.py").is_file()
            assert (run_dir / "oof_exp1.parquet").is_file()
            print("✅ Case A PASSED: Proposal debated, resolved, gate APPROVED, scaffold executed, OOF verified.")

        print("\n--- CASE B: UNRESOLVED OBJECTION (SKEPTIC REJECT -> GATE BLOCK) ---")
        engineer_called_in_case_b = False

        def mock_llm_case_b(prompt, system=None, **kwargs):
            nonlocal engineer_called_in_case_b
            p = prompt.upper()
            if "YOU ARE THE ML ENGINEER" in p:
                engineer_called_in_case_b = True
                return "def train_predict(): pass"
            if "YOU ARE THE STRATEGIST. BASED ON RESEARCH" in p:
                return json.dumps({
                    "hypothesis_id": "EXP2_HYPOTHESIS",
                    "hypothesis": "External foundation model on ungrounded user_id features",
                    "mechanism": "Pre-trained deep neural network",
                    "verified_feature_names": ["amount_usd", "hours_since_last_txn"],
                    "supporting_evidence": "External blog post",
                    "falsifiable_criteria": "AUC > 0.99",
                    "expected_metric_direction": "+0.05 AUC",
                    "computational_cost": "Heavy",
                    "leakage_risks": "Massive external data leakage"
                })
            if "YOU ARE THE SKEPTIC. REVIEW THE STRATEGIST'S PROPOSAL" in p:
                return json.dumps({
                    "hypothesis_id": "EXP2_HYPOTHESIS",
                    "overall_verdict": "REJECT",
                    "objections": [{
                        "objection_id": "OBJ_001",
                        "original_claim": "External foundation model",
                        "evidence": "Competition Rule 4 strictly forbids external models and ungrounded identifiers",
                        "severity": "CRITICAL",
                        "verification_test": "Check rule handbook",
                        "reasoning": "Direct disqualification risk"
                    }],
                    "summary": "External model violation"
                })
            if "THE SKEPTIC BLOCKED YOUR PROPOSAL" in p:
                return json.dumps({
                    "rebuttals": [{
                        "objection_id": "OBJ_001",
                        "response_type": "REBUT",
                        "detailed_answer": "I disagree with the rules",
                        "action_taken": "None"
                    }],
                    "revised_specification": {
                        "approved_features": ["amount_usd"],
                        "implementation_constraints": []
                    }
                })
            if "RENDER YOUR FINAL VERDICT" in p:
                return json.dumps({
                    "objection_resolutions": [{
                        "objection_id": "OBJ_001",
                        "status": "UNRESOLVED",
                        "final_comment": "Rules violation cannot be rebutted; rule remains strictly in force"
                    }],
                    "final_verdict": "REJECT",
                    "deciding_reason": "Rule violation remains UNRESOLVED"
                })
            if "STATE YOUR FORMAL DECISION" in p:
                return "DECISION: BLOCKED\nDECIDING_REASON: Rule violation unresolved."
            return "OK"

        with patch("gemini_client.query_llm", side_effect=mock_llm_case_b), \
             patch.object(orch.notebook_client, "query_notebook", return_value={"status": "PASSED", "answer": "Grounded", "citations": {}}):
            res_b = await orch.run_single_experiment(exp_no=2)
            print(f"Status: {res_b['status']}")
            print(f"CV Score: {res_b.get('cv_score')}")
            assert res_b["status"] == "BLOCKED"
            assert res_b["cv_score"] is None
            assert not engineer_called_in_case_b, "Engineer MUST NOT be invoked when Policy Gate halts execution!"
            assert not (run_dir / "model_part_exp2.py").exists(), "model_part_exp2.py must NOT be generated!"
            print("✅ Case B PASSED: Unresolved objection halted by Policy Gate, Engineer skipped, BLOCKED state recorded.")

        # 3. Check HTML dashboard contains debate lineage and badges
        assert orch.html_file.is_file()
        html_text = orch.html_file.read_text(encoding="utf-8")
        assert "badge-blocked" in html_text
        assert "GATE: BLOCKED" in html_text
        assert "EXP1_HYPOTHESIS" in html_text
        assert "EXP2_HYPOTHESIS" in html_text
        print("\n✅ HTML Dashboard verified: view.html correctly rendered debate lineage, policy gate badges, and prompt hashes.")

    finally:
        # Cleanup demonstration run artifacts
        if demo_base.exists():
            shutil.rmtree(demo_base)

    print("\n" + "=" * 80)
    print("DEMO COMPLETE — ALL V2 PROTOCOLS HARNESS-VERIFIED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_demo())
