---
name: autonomous-research-protocol
description: Master autonomous research protocol skill for Antigravity. Enforces the complete 8-pillar lifecycle (inheritance, independent discovery, reciprocal relay, experiment planning, execution, dual ledger, independent verification, and continuation gating).
---

# Autonomous Research & Execution Protocol Orchestrator

## Overview

Use this skill to orchestrate, supervise, or execute end-to-end autonomous research, experimentation, and scientific investigation pipelines. This skill enforces strict adherence to [AUTONOMOUS_RESEARCH_PROTOCOL.md](file:///home/kizamladjanijebac/.gemini/antigravity/worktrees/discord-openclaw/analyze_discord_openclaw_setup/AUTONOMOUS_RESEARCH_PROTOCOL.md).

## Operational Workflow

When running an autonomous research campaign, execute the following 8 stages sequentially:

### 1. Predecessor Ingestion
- Read `objective.md`, `experiments/local_leaderboard.md`, `findings/negative_findings.md`, and `findings/positive_invariants.md`.
- Verify the baseline environment, dataset splits, and metric calculation sanity.

### 2. Independent Discovery
- Dispatch two or more independent researchers (or subagents) with isolated contexts.
- Ensure researchers explore without viewing concurrent peer drafts.
- Verify output artifacts: `research/discoveries/discovery_<id>.md`.

### 3. Reciprocal Knowledge Relay
- Exchange discovery reports between researchers without debate.
- Agent A extends Agent B's discoveries (`research/discoveries/relay_A.md`).
- Agent B extends Agent A's discoveries (`research/discoveries/relay_B.md`).
- Focus strictly on source expansion, missing variables, and experiment proposals.

### 4. Experiment Planning
- Formalize falsifiable hypotheses in `research/hypotheses.md` (ID, Statement, Justification, Falsification Boundary, Delta, Expected Info Gain).
- Enqueue planned configurations in `planning/experiment_queue.json`.

### 5. Continuous Execution & Benchmarking
- Execute experiments using leak-free Cross-Validation.
- Persist out-of-fold predictions to `predictions/oof_<exp_id>.parquet`.
- Update `experiments/experiment_log.md` and rank in `experiments/local_leaderboard.md`.

### 6. Dual Findings Ledger
- For improvements: update `findings/positive_invariants.md`.
- For failures/neutral outcomes: MANDATORY recording in `findings/negative_findings.md` with root cause and negative constraints.

### 7. Independent Verification
- Dispatch an isolated Verifier agent to audit artifacts, verify data hashes, independently recompute metrics, and check for leakage.
- Record signed verdict in `verification/evidence.md`.

### 8. Continuation Gating
- Apply quantitative stopping criteria:
  - Budget cap (iteration or wall-time).
  - Plateau rule ($K=3$ consecutive runs with $\Delta < 0.001$).
  - Target benchmark achieved.
- Apply pivot rule if failure rate $>60\%$.
- Log next phase plan to `planning/next_actions.md` and update `state.json`.
