# PRD: Autonomous Research & Execution Protocol for Antigravity

**Document:** `prd_autonomous_research_protocol.md`  
**Status:** DRAFT → REFINED  
**Target:** Permanent Antigravity Master Protocol & Global Skills

---

## 1. Executive Summary & Objective

The **Autonomous Research & Execution Protocol** establishes a standardized, reproducible, and verifiable framework for autonomous multi-agent scientific, algorithmic, and engineering research in Antigravity. It eliminates unstructured conversational debates, hallucinations, data leakage, and unverified success claims by enforcing a strict disk-backed state machine:
`Inherit Previous Work → Independent Discovery → Reciprocal Relay → Experiment Planning → Continuous Execution & Benchmarking → Positive & Negative Ledger → Independent Verification → Continuation Gating`.

Once implemented, this protocol operates permanently as core Antigravity skills (`autonomous-research-protocol`, `research-discovery`, `research-relay`, `experiment-runner`, `evidence-verifier`) and foundational documentation referenced across all research projects.

---

## 2. Machine-Checkable Acceptance Criteria (Citadel Specification)

Each of the 8 pillars must satisfy concrete, machine-checkable requirements:

### AC-1: Inheritance of Previous Work
- **AC-1.1:** Protocol requires explicit reading and parsing of predecessor artifacts (`objective.md`, `local_leaderboard.md`, `findings/negative_findings.md`, `research/sources.md`).
- **AC-1.2:** System validates baseline metrics and environment state before opening new tasks.

### AC-2: Independent Discovery
- **AC-2.1:** Exploration phase mandates procedural isolation: agents research without access to concurrent peer working drafts, preventing anchoring bias.
- **AC-2.2:** Each agent outputs a dedicated discovery report matching schema: `research/discoveries/discovery_<agent_id>.md`.

### AC-3: Reciprocal Research Relay (Non-Adversarial Knowledge Exchange)
- **AC-3.1:** Replaces agent-to-agent debate with reciprocal baton exchange: Agent A reads `discovery_B.md` to output `relay_A.md`; Agent B reads `discovery_A.md` to output `relay_B.md`.
- **AC-3.2:** Explicit prohibition of argumentative dispute; focus strictly on source expansion, missing variables, hypothesis formalization, and experiment design.

### AC-4: Formal Experiment Planning
- **AC-4.1:** All experiments require a falsifiable hypothesis schema: `ID`, `Hypothesis Statement`, `Theoretical Justification`, `Falsification Boundary`, `Target Metric`, `Expected Info Gain`.
- **AC-4.2:** Experiment queue recorded in structured format (`planning/experiment_queue.json`) with strict parameter grids and CV split seeds.

### AC-5: Continuous Execution & Empirical Benchmarking
- **AC-5.1:** Execution requires leakage-free Cross-Validation (K-Fold, Stratified, or TimeSeries) where preprocessing fits only on training folds.
- **AC-5.2:** Out-Of-Fold (OOF) predictions must be persisted to disk (`predictions/oof_<exp_id>.parquet` or `.csv`).
- **AC-5.3:** Metrics automatically logged to `experiments/experiment_log.md` and sorted into `experiments/local_leaderboard.md`.

### AC-6: Dual Findings Ledger (Positive & Negative)
- **AC-6.1:** Positive findings cataloged in `findings/positive_invariants.md` with verified metric delta and statistical significance.
- **AC-6.2:** Mandatory cataloging in `findings/negative_findings.md` for failed, neutral, or regressive experiments to avoid cyclic re-testing and capture dead ends.

### AC-7: Independent Verification
- **AC-7.1:** Verification conducted by a separate agent identity or isolated process with skeptic mandate.
- **AC-7.2:** Verifier re-computes metric from ground truth and saved predictions, re-runs execution verification scripts, and logs cryptographic evidence in `verification/evidence.md`.

### AC-8: Continuation, Pivot & Stopping Gating
- **AC-8.1:** Quantitative stopping conditions:
  - Budget cap (maximum iterations $N$ or wall-time).
  - Metric plateau ($\Delta < 0.001$ over $K=3$ consecutive runs).
  - Target benchmark achieved.
- **AC-8.2:** Pivot trigger: Failure rate $>60\%$ in a paradigm forces hypothesis branch switch.
- **AC-8.3:** Continuation gate: Next iteration is blocked unless current milestone passes independent verification. Decision logged to `planning/next_actions.md` and `state.json`.

---

## 3. Architecture & Artifact Manifest

The implementation delivers:
1. `AUTONOMOUS_RESEARCH_PROTOCOL.md` — Complete master standard and workflow documentation.
2. `skills/autonomous-research-protocol/SKILL.md` — Antigravity master orchestration skill.
3. `skills/research-discovery/SKILL.md` — Independent discovery skill.
4. `skills/research-relay/SKILL.md` — Reciprocal knowledge relay skill.
5. `skills/experiment-runner/SKILL.md` — Execution, benchmarking, and CV tracking skill.
6. `skills/evidence-verifier/SKILL.md` — Skeptical independent verification skill.
7. `templates/autonomous-research/` — Workspace scaffold template and generator script.
8. Global symlinks into `~/.gemini/config/skills/` and `~/.gemini/antigravity/skills/` for permanent Antigravity runtime persistence.
