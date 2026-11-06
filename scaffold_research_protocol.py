#!/usr/bin/env python3
"""
Scaffolder for Autonomous Research & Execution Protocol.
Initializes a fully compliant directory structure with standard markdown contracts.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone

def scaffold_research_workspace(target_dir: Path, objective_title: str):
    target_dir = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    dirs = [
        target_dir / "research" / "discoveries",
        target_dir / "experiments",
        target_dir / "findings",
        target_dir / "predictions",
        target_dir / "verification",
        target_dir / "planning",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. objective.md
    obj_file = target_dir / "objective.md"
    if not obj_file.exists():
        obj_file.write_text(f"""# Objective: {objective_title}

**Initialized:** {now}  
**Status:** ACTIVE

## 1. Problem Statement & Baseline
- **Goal:** [Define specific research goal]
- **Baseline Metric:** [e.g. CV AUC = 0.69796]
- **Target Metric:** [e.g. CV AUC >= 0.70500]

## 2. Hard Constraints
- Leak-free cross validation required.
- All OOF predictions persisted to disk.
- Independent verification mandatory before milestone progression.
- Plateau threshold: Δ < 0.001 over 3 consecutive runs triggers stopping/pivot.
""", encoding="utf-8")

    # 2. state.json
    state_file = target_dir / "state.json"
    if not state_file.exists():
        state_file.write_text(json.dumps({
            "protocol_version": "1.0",
            "initialized_at": now,
            "current_phase": "INHERITANCE",
            "iteration": 0,
            "max_iterations": 10,
            "consecutive_plateaus": 0,
            "consecutive_failures": 0,
            "best_verified_metric": None,
            "baseline_metric": None,
            "halted": False,
            "halt_reason": None
        }, indent=2), encoding="utf-8")

    # 3. research/sources.md
    sources_file = target_dir / "research" / "sources.md"
    if not sources_file.exists():
        sources_file.write_text("""# Research Sources & Literature Citations

| ID | Title / Repository | URL / Citation | Relevance / Key Takeaways | Date Added |
|---|---|---|---|---|
| SRC-001 | Baseline Architecture | - | Baseline implementation and initial benchmarks | Initial |
""", encoding="utf-8")

    # 4. research/hypotheses.md
    hyp_file = target_dir / "research" / "hypotheses.md"
    if not hyp_file.exists():
        hyp_file.write_text("""# Formal Research Hypotheses

| ID | Hypothesis Statement | Theoretical Justification | Parameter / Intervention Delta | Falsification Boundary | Status |
|---|---|---|---|---|---|
""", encoding="utf-8")

    # 5. experiments/experiment_log.md
    exp_log = target_dir / "experiments" / "experiment_log.md"
    if not exp_log.exists():
        exp_log.write_text(f"""# Experiment Execution Log

Log initialized at {now}.
""", encoding="utf-8")

    # 6. experiments/local_leaderboard.md
    lb_file = target_dir / "experiments" / "local_leaderboard.md"
    if not lb_file.exists():
        lb_file.write_text("""# Local Leaderboard

| Rank | Experiment ID | Hypothesis ID | CV Metric (Mean ± Std) | Baseline Δ | Verified | Commit Hash | Date |
|---|---|---|---|---|---|---|---|
""", encoding="utf-8")

    # 7. findings/positive_invariants.md
    pos_file = target_dir / "findings" / "positive_invariants.md"
    if not pos_file.exists():
        pos_file.write_text("""# Positive Invariants Ledger

Documented architectural, algorithmic, and parameter configurations with verified empirical gains.

| ID | Discovery | Empirical Delta | Verification Ref | Date |
|---|---|---|---|---|
""", encoding="utf-8")

    # 8. findings/negative_findings.md
    neg_file = target_dir / "findings" / "negative_findings.md"
    if not neg_file.exists():
        neg_file.write_text("""# Negative Findings Graveyard (Mandatory Failure Ledger)

Every failed hypothesis, regression, bug, or computational dead end MUST be logged here to prevent recursive agent loops.

| Exp ID | Hypothesis Tested | Observed vs Expected | Root Cause Analysis | Invariant / Negative Rule | Date |
|---|---|---|---|---|---|
""", encoding="utf-8")

    # 9. verification/evidence.md
    ev_file = target_dir / "verification" / "evidence.md"
    if not ev_file.exists():
        ev_file.write_text(f"""# Independent Verification Evidence Ledger

Initialized {now}.
""", encoding="utf-8")

    # 10. planning/experiment_queue.json
    q_file = target_dir / "planning" / "experiment_queue.json"
    if not q_file.exists():
        q_file.write_text(json.dumps({
            "queue": []
        }, indent=2), encoding="utf-8")

    # 11. planning/next_actions.md
    actions_file = target_dir / "planning" / "next_actions.md"
    if not actions_file.exists():
        actions_file.write_text("""# Next Actions & Phase Gating

## Current Status
- [ ] Phase 1: Predecessor Work Ingestion
- [ ] Phase 2: Independent Discovery
- [ ] Phase 3: Reciprocal Relay
- [ ] Phase 4: Formal Experiment Planning
- [ ] Phase 5: Continuous Execution & Benchmarking
- [ ] Phase 6: Dual Findings Ledger Update
- [ ] Phase 7: Independent Verification
- [ ] Phase 8: Continuation / Stopping Decision
""", encoding="utf-8")

    print(f"✅ Successfully scaffolded Autonomous Research Workspace at: {target_dir}")

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./autonomous_research_workspace")
    title = sys.argv[2] if len(sys.argv) > 2 else "Autonomous Research Task"
    scaffold_research_workspace(target, title)
