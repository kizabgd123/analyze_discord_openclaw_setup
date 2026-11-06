# Task Plan: Implement Autonomous Research Relay Workflow in Hermes

## Goal
Implement a reusable, autonomous research and execution workflow in the existing Hermes environment using native Hermes Kanban and Discord integration, following the "Independent Discovery → Research Relay → Execution → Verification → Continuous Improvement" methodology.

## Current Phase
Phase 4: Acceptance Test on Kanban Board

## Phases

### Phase 1: Requirements, Inspection & Planning
- [x] Review `/home/kizamladjanijebac/Downloads/kaggle_agentic_workflow_research.md`
- [x] Inspect existing Hermes installation, profiles, skills, tools, Kanban DB, and gateway
- [x] Create persistent planning files (`task_plan.md`, `findings.md`, `progress.md`)
- [x] Document inspection findings and baseline state in `findings.md`
- **Status:** complete

### Phase 2: Dedicated Skills Design & Creation
- [x] Create `SKILL.md` for `research-orchestrator`
- [x] Create `SKILL.md` for `independent-researcher`
- [x] Create `SKILL.md` for `research-relay`
- [x] Create `SKILL.md` for `experiment-engineer`
- [x] Create `SKILL.md` for `evidence-verifier`
- [x] Install skills to `~/.hermes/skills/research-relay/` and deploy to profile skill directories
- [x] Validate skill discovery and CLI compatibility
- **Status:** complete

### Phase 3: Profile Roles & Reusable Workspace Scaffold
- [x] Configure/verify Hermes profiles (`default` orchestrator, `kiza` researcher/experimenter, `kreten` researcher/verifier)
- [x] Build reusable research workspace template generator (`templates/research-workspace/` and `scaffold_workspace.py`)
- [x] Define workspace contracts:
  - `objective.md`
  - `research/discoveries/`
  - `research/sources.md`
  - `research/hypotheses.md`
  - `experiments/experiment_log.md`
  - `experiments/local_leaderboard.md`
  - `verification/evidence.md`
  - `planning/next_actions.md`
- **Status:** complete

### Phase 4: Acceptance Test on Kanban Board
- [x] Define small, harmless test objective based on Kaggle research methodology
- [x] Scaffolding test workspace
- [x] Create Kanban task graph with explicit dependencies and contracts
- [x] Run Independent Discovery (Researcher 1 & Researcher 2 work independently)
- [x] Run Research Relay (exchange completed reports, extend findings without debate)
- [x] Run Experiment Engineer execution (run benchmark/experiment, log metrics to leaderboard)
- [x] Run Evidence Verifier (verify code execution, hashes, fold separation, artifact validity)
- [x] Orchestrator review & final consolidation
- **Status:** complete ✅ — All 5 Kanban tasks done, Verifier Verdict: PASS

### Phase 5: Final Audit & Deliverables Report
- [x] Verify actual artifacts, execution logs, and Kanban history
- [x] Run pre-commit checks and JudgeGuard verification
- [x] Produce comprehensive final report covering changes, backup paths, tests, results, and proof (`RESEARCH_RELAY_DELIVERABLES.md`)
- [x] Git commit all Phase 4 & 5 changes
- **Status:** complete ✅

## Autonomous Research Engine (7 Pillars Methodology)

### Phase R1: Decoupling & Skills Upgrade for 7 Pillars
- [x] Remove communication channel dependencies from skills & profiles (pure native Hermes Kanban + persistent filesystem)
- [x] Upgrade `research-relay` skill: Add explicit Reciprocal Relay specifications (`relay_A.md` and `relay_B.md`, extending peer findings)
- [x] Upgrade `research-orchestrator` skill: Add 7-pillar architecture, Hypothesis Engine ranking & Kanban dependency assignment
- [x] Upgrade `experiment-engineer` skill: Add autonomous consecutive experimentation logic (post-run delta analysis vs baseline, leaderboard update, automated next task proposal)
- [x] Upgrade `evidence-verifier` skill: Add isolated execution & methodological constraint verification
- [x] Sync updated skills to `~/.hermes/skills/research-relay/` and profile directories
- **Status:** complete ✅

### Phase R2: Reciprocal Research Relay & Hypothesis Engine Execution
- [x] Verify Independent Discoveries exist: `kiza_discoveries.md` and `kreten_discoveries.md`
- [x] Create Reciprocal Relay Kanban task for `kiza`: read `kreten_discoveries.md`, generate `research/discoveries/relay_kiza.md` (`t_21aa1061`)
- [x] Create Reciprocal Relay Kanban task for `kreten`: read `kiza_discoveries.md`, generate `research/discoveries/relay_kreten.md` (`t_763c3ee7`)
- [x] Execute both reciprocal relay tasks via Hermes Kanban (both marked `done`, execution verified)
- [x] Orchestrator Hypothesis Engine: synthesize `relay_kiza.md` + `relay_kreten.md` into ranked `research/hypotheses.md` (HYP_001, HYP_002, HYP_003)
- **Status:** complete ✅

### Phase R3: Autonomous Experimentation — Consecutive Cycles (EXP_001 & EXP_002)
- [x] Cycle 1 (EXP_001): OOF Target Encoding baseline vs Regularization (completed baseline, AUC=0.6981)
- [x] Cycle 2 (EXP_002): Autonomous next experiment formulated from HYP_002 (M-estimate parameter grid sensitivity: m in [0, 1000])
- [x] Execute EXP_002 via Experiment Engineer on Kanban (`t_eb661e8b`) — autonomous execution verified (completed in 71s)
- [x] Record results in `experiments/experiment_log.md` and update `experiments/local_leaderboard.md`
- [x] Formulate evidence-based next action in `planning/next_actions.md` (EXP_003 formulated)
- **Status:** complete ✅

### Phase R4: Strengthened Independent Verification in Isolated Context
- [x] Isolated verification task assigned on Kanban to Evidence Verifier (`kreten`: `t_cf9f352e`)
- [x] Verify EXP_001 and EXP_002 artifacts, SHA256 checksums, script execution exit codes (0 discrepancies)
- [x] Audit fold leakage constraints (verify target values are completely separated across folds — 0% leakage)
- [x] Produce comprehensive verification report in `verification/evidence.md` with final PASS verdict (AUD_001 & AUD_002: PASS)
- **Status:** complete ✅

### Phase R5: Persistent Knowledge Audit & Comprehensive Acceptance Report
- [x] Verify all 7 pillars have complete file-backed persistence without data loss
- [x] Pre-commit hook & JudgeGuard post-check
- [x] Generate comprehensive acceptance artifact `AUTONOMOUS_RESEARCH_ENGINE_DELIVERABLES.md`
- [x] Git commit all changes
- **Status:** complete ✅

## Final Audit & Scientific Precision Verification

### Phase A1: Correct EXP_002 Reporting & Scope in Research Workspace Files
- [x] Correct `experiment_log.md`: distinguish peak mean Val AUC at $m=10.0$ from minimum fold std dev at $m=1000.0$.
- [x] Clarify 5-fold CV vs external test performance across all logs.
- [x] Correct `hypotheses.md`: update `HYP_001` and `HYP_002` scope to OOF CV validation AUC (not test AUC).
- [x] Refute hypothesis that peak AUC and minimum fold variance coincide (`HYP_002_SUB`).
- [x] Update `local_leaderboard.md` to clearly present the Performance Champion ($m=10.0$) and Stability Champion ($m=1000.0$).
- [x] JudgeGuard pre/post checks and Git commit `f07d6dd`.
- **Status:** complete ✅

### Phase A2: Strengthen Independent Verification & Document Continuation Contract
- [x] Expand `verification/evidence.md`: document evidence of fresh isolated verifier context (profile `kreten`, worker PID 1969005, subshell, filesystem path).
- [x] Conduct and document dual-side code inspection of `MEstimateOOFEncoder.fit_transform`:
  - Validation-side: 0% target leakage, partition-by-partition mapping, unseen level handling.
  - Training-side: loop overwriting mechanism, difference between composite array evaluation vs strict in-loop fold evaluation (0.75167 vs 0.75067 Train AUC).
- [x] Document exact reproducibility inputs, seeds (`seed=42`), distributions, scripts, and SHA256 hashes.
- [x] Document autonomous continuation contract in `planning/next_actions.md`:
  - Genesis of EXP_003 from EXP_002.
  - Enforcement of resource limits and stopping conditions (milestone budget, metric plateau rule, Kanban parent gating).
  - Explicit documentation of what remains unexecuted (`t_exp_003` queued, holdout test unexecuted).
- [x] JudgeGuard pre/post checks and Git commit `557333e`.
- **Status:** complete ✅

### Phase A3: Update Comprehensive Acceptance Report & Produce Final Audit Report
- [x] Update `AUTONOMOUS_RESEARCH_ENGINE_DELIVERABLES.md` in brain directory with corrected reporting, refined scopes, dual-side code inspection, exact reproducibility data, and continuation governance.
- [x] Generate standalone `FINAL_AUDIT_REPORT.md` separating Verified Facts, Reported Claims, Corrected Conclusions, and Remaining Limitations.
- [x] Update `task_plan.md` and `progress.md`.
- [x] JudgeGuard pre/post checks and Git commit.
- **Status:** complete ✅

## Scientific Validation Phase

### Phase SV1: Deep Scientific Validation of Four Core Methodological Points
- [x] **Point 1 (OOF Correctness & Terminology):**
  - Verify validation-side zero leakage: confirmed 0 index overlap across all 5 folds, targets completely excluded.
  - Audit training-side `train_encoded`: prove row's own target is included in fold-map groupby (in-sample memorization), explain 4x loop overwriting.
  - Recalculate affected metrics: clarify Train AUC (0.75167) as in-sample composite diagnostic; update terminology in `experiment_log.md` and `local_leaderboard.md`.
- [x] **Point 2 (Parameter Selection & Nested CV):**
  - Distinguish flat 5-fold grid optimum from independently validated optimum.
  - Implement and execute nested 5-outer × 3-inner cross-validation.
  - Document results: Nested CV Test AUC = 0.69796 ± 0.01377; selection optimism = 0.00019; modal optimum = m=10.0 (3/5 folds).
- [x] **Point 3 (Verifier Isolation: Process vs Knowledge):**
  - Document process isolation: separate profiles (`kiza` vs `kreten`), separate OS PIDs (1965442 vs 1969005), separate runs (#18 vs #19), subshell memory isolation.
  - Document knowledge isolation boundaries: shared filesystem directory, same underlying LLM weights (`gemma4:31b-cloud`), author's summaries visible.
  - Clarify that isolation is procedural/process-level, not full double-blind scientific review.
- [x] **Point 4 (Continuation/Stopping & Execution Gating):**
  - Verify system-enforced gates: Kanban parent-child dependency (`parents: ['t_eb661e8b']`), worker timeouts (600s), retry caps (max 2).
  - Verify procedural policies: 2-cycle milestone budget, metric plateau stopping rule ($\Delta < 0.001$).
  - Confirm execution state: `t_exp_003` is NOT on Kanban board (confirmed via `hermes kanban list`), remains completely unexecuted.
- [x] Author comprehensive `SCIENTIFIC_VALIDATION_REPORT.md` artifact in brain directory.
- [x] Maintain `WORK_LOG.md`, run JudgeGuard post-check, and commit Phase SV1.
- **Status:** complete ✅
1. How to coordinate Research Relay without bot-to-bot chat?
   *Answer*: Via Hermes Kanban cards, artifact references (`discoveries/<agent>.md`), and dependency gating. Agents write to disk; next stage reads from disk.
2. How to ensure independent discovery?
   *Answer*: Researchers are dispatched to separate tasks without access to the peer's concurrent output until the relay stage is triggered.
3. How to keep unverified hypotheses distinct from confirmed findings?
   *Answer*: Strict directory separation between `research/hypotheses.md` (unverified/in-testing) and `verification/evidence.md` (independently validated).

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Use file-backed persistent research workspace | Context windows are ephemeral; disk files provide auditable, reproducible history across agent runs. |
| Non-adversarial Research Relay | Kaggle S6E8 methodology proves agents extend and build on each other's discoveries rather than wasting tokens in unstructured debate. |
| Kanban-gated dependency execution | Hermes native Kanban natively supports task dependencies (`parent_id`), ensuring experiment execution only starts when prerequisites pass. |
| Strict Pre-Action Verification | Mandatory compliance with `MASTER_ORCHESTRATION.md` and `judge_guard.py` before each phase and commit. |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| (None yet in this run) | - | - |
