# Findings & Decisions: Autonomous Research Relay Workflow

## Requirements
- **Goal:** Implement reusable, autonomous research and execution workflow in existing Hermes environment.
- **Key Constraints:**
  - Reuse existing Hermes installation, profiles, skills, tools, Kanban, Discord integration.
  - DO NOT reinstall Hermes or create duplicate infrastructure.
  - Core methodology: `Independent Discovery → Research Relay → Execution → Verification → Continuous Improvement`.
  - Non-adversarial Research Relay: agents extend each other's discoveries, NO bot-to-bot debate.
  - Persistent research memory with standard files (`objective.md`, `research/discoveries/`, `research/sources.md`, `research/hypotheses.md`, `experiments/experiment_log.md`, `experiments/local_leaderboard.md`, `verification/evidence.md`, `planning/next_actions.md`).
  - Strict verification: a task is not complete because an agent claims success. Check actual artifacts, execution logs, reproducibility.
  - Small end-to-end acceptance test with full auditable proof.

## Research Findings
- **Hermes Installation:**
  - Binary: `/home/kizamladjanijebac/.local/bin/hermes` (Hermes Agent v0.21.3, upstream 98f758ae).
  - Config home: `/home/kizamladjanijebac/.hermes`.
  - Kanban DB: `/home/kizamladjanijebac/.hermes/kanban.db` (native SQLite schema with tasks, boards, dependencies, context).
  - Toolsets: `kanban` toolset enabled on platform `discord`.
  - Service: `hermes-gateway.service` (systemd user service, PID 25777, embeds Kanban dispatcher).
- **Profiles:**
  - `default`: Orchestrator (entry point, task decomposition, acceptance criteria).
  - `kiza`: Researcher / Experiment Engineer (Ollama `gemma4:31b-cloud`).
  - `kreten`: Researcher / Evidence Verifier (Ollama `gemma4:31b-cloud`).
- **Kaggle Agentic Workflow Ground Truth (`kaggle_agentic_workflow_research.md`):**
  - S6E5 (Autonomous Codex): Iterative experimentation cycle, `local_leaderboard.md`, leakage-free CV, storing OOF/test predictions on disk.
  - S6E8 (Distributed Intelligence & AI Relay): Post-hoc team expansion; two agents investigate independently, write `discoveries.md`, then exchange reports to extend rather than debate; human sets budget, goals, stop conditions.
  - S6E3 (KGMON Playbook): Standardized ML lifecycle (EDA → Feature Engineering → Baselines → Stacking → Verification); record both good and failed experiments.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Skills directory under `~/.hermes/skills/research-relay/` | Keeps new research skills organized in a dedicated domain folder while being automatically discoverable by Hermes. |
| Mirror skills to profile paths | `~/.hermes/profiles/kiza/skills/` and `~/.hermes/profiles/kreten/skills/` allow profile-specific autonomy when invoking specialized tools. |
| Standardized Markdown schema for `discoveries.md` | Ensures researchers output structured evidence, sources, hypotheses, failed attempts, and open questions so the peer researcher can immediately parse and extend them. |
| Kanban task cards hold explicit file references | Context is transferred via filesystem paths (`file://...`) passed in task descriptions and acceptance criteria. |
| Verifier is strictly read-only on claims, active on verification | Verifier executes code independently to check exit codes, output files, checksums, and cross-validation integrity without modifying raw experimental evidence. |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| Network probes hang on `hermes profile list` | Inspect `~/.hermes/profiles` and profile yaml files directly via filesystem tools rather than triggering interactive network discovery. |

## Resources
- Ground truth research: `/home/kizamladjanijebac/Downloads/kaggle_agentic_workflow_research.md`
- Hermes documentation & tools: `/home/kizamladjanijebac/.hermes/`
