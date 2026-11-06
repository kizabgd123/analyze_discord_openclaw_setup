# Task Plan: Implement Autonomous Research Relay Workflow in Hermes

## Goal
Implement a reusable, autonomous research and execution workflow in the existing Hermes environment using native Hermes Kanban and Discord integration, following the "Independent Discovery → Research Relay → Execution → Verification → Continuous Improvement" methodology.

## Current Phase
Phase 1: Requirements, Inspection & Planning

## Phases

### Phase 1: Requirements, Inspection & Planning
- [x] Review `/home/kizamladjanijebac/Downloads/kaggle_agentic_workflow_research.md`
- [x] Inspect existing Hermes installation, profiles, skills, tools, Kanban DB, and gateway
- [x] Create persistent planning files (`task_plan.md`, `findings.md`, `progress.md`)
- [ ] Document inspection findings and baseline state in `findings.md`
- **Status:** in_progress

### Phase 2: Dedicated Skills Design & Creation
- [ ] Create `SKILL.md` for `research-orchestrator`
- [ ] Create `SKILL.md` for `independent-researcher`
- [ ] Create `SKILL.md` for `research-relay`
- [ ] Create `SKILL.md` for `experiment-engineer`
- [ ] Create `SKILL.md` for `evidence-verifier`
- [ ] Install skills to `~/.hermes/skills/research-relay/` and deploy to profile skill directories
- [ ] Validate skill discovery and CLI compatibility
- **Status:** pending

### Phase 3: Profile Roles & Reusable Workspace Scaffold
- [ ] Configure/verify Hermes profiles (`default` orchestrator, `kiza` researcher/experimenter, `kreten` researcher/verifier)
- [ ] Build reusable research workspace template generator (`templates/research-workspace/` and `scaffold_workspace.py`)
- [ ] Define workspace contracts:
  - `objective.md`
  - `research/discoveries/`
  - `research/sources.md`
  - `research/hypotheses.md`
  - `experiments/experiment_log.md`
  - `experiments/local_leaderboard.md`
  - `verification/evidence.md`
  - `planning/next_actions.md`
- **Status:** pending

### Phase 4: Acceptance Test on Kanban Board
- [ ] Define small, harmless test objective based on Kaggle research methodology
- [ ] Scaffolding test workspace
- [ ] Create Kanban task graph with explicit dependencies and contracts
- [ ] Run Independent Discovery (Researcher 1 & Researcher 2 work independently)
- [ ] Run Research Relay (exchange completed reports, extend findings without debate)
- [ ] Run Experiment Engineer execution (run benchmark/experiment, log metrics to leaderboard)
- [ ] Run Evidence Verifier (verify code execution, hashes, fold separation, artifact validity)
- [ ] Orchestrator review & final consolidation
- **Status:** pending

### Phase 5: Final Audit & Deliverables Report
- [ ] Verify actual artifacts, execution logs, and Kanban history
- [ ] Run pre-commit checks and JudgeGuard verification
- [ ] Produce comprehensive final report covering changes, backup paths, tests, results, and proof
- **Status:** pending

## Key Questions
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
