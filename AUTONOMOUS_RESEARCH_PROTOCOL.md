# Autonomous Research & Execution Protocol

**Document Version:** 1.0  
**Status:** ACTIVE  
**Applicability:** Universal standard for all Antigravity autonomous research, experimentation, and ML/scientific pipelines.

---

## 1. Core Principles

The Autonomous Research & Execution Protocol governs multi-agent collaborative investigation without conversational noise, anchoring bias, data leakage, or unverified claims. It enforces 8 immutable procedural stages:

```
[Inherit Previous Work]
          │
          ▼
 [Independent Discovery] (Agent A || Agent B)
          │
          ▼
   [Reciprocal Relay]    (Agent A ⇆ Agent B baton exchange)
          │
          ▼
 [Experiment Planning]   (Falsifiable Hypotheses & Strict Schema)
          │
          ▼
[Continuous Execution]   (Leak-Free CV & Out-of-Fold Logging)
          │
          ▼
 [Dual Findings Ledger]  (Positive Invariants & Negative Graveyard)
          │
          ▼
[Independent Verifier]   (Isolated Skeptic Audit & Reproducibility)
          │
          ▼
 [Continuation Gating]   (Plateau, Budget, Pivot & Stopping Checks)
```

---

## 2. The Eight Protocol Pillars

### Pillar 1: Predecessor Work Inheritance (How Agents Resume)
1. **Context Ingestion:** Every research agent beginning work on a project must first read:
   - `objective.md` — The target problem, constraints, and baseline goals.
   - `experiments/local_leaderboard.md` — All prior experiments, parameters, and verified scores.
   - `findings/negative_findings.md` — The catalogue of failed attempts to avoid repeating loops.
   - `findings/positive_invariants.md` — Proven structural gains that must be preserved.
   - `research/sources.md` — Verified academic papers, repos, and literature.
2. **State Validation:** Verify that current data files, environment packages, and baseline benchmark scores match recorded ground truth before opening new tracks.

### Pillar 2: Independent Discovery (How Agents Research)
1. **Procedural Isolation:** Initial discovery must run with isolated agent contexts (separate subagents, separate subshells, or distinct role prompts). Agents do NOT observe each other’s concurrent initial brainstorming.
2. **Anchoring Prevention:** Preventing early groupthink allows Agent A to explore unconventional literature or feature families while Agent B explores structural, mathematical, or hyperparameter paradigms.
3. **Output Contract:** Each agent produces a structured discovery report:
   - Path: `research/discoveries/discovery_<agent_id>.md`
   - Sections:
     1. Domain Background & Literature Ingested
     2. Proposed Mechanistic Insights
     3. Initial Hypotheses
     4. Identified Risk Factors & Edge Cases
     5. Open Questions

### Pillar 3: Reciprocal Knowledge Relay (How Agents Exchange Discoveries)
1. **Baton Passing Over Debate:** Agents never engage in argumentative chatter, persona squabbling, or philosophical debate.
2. **Reciprocal Exchange:**
   - Agent A reads Agent B's `discovery_B.md` and generates `research/discoveries/relay_A.md`.
   - Agent B reads Agent A's `discovery_A.md` and generates `research/discoveries/relay_B.md`.
3. **Extension Mandate:** Each relay agent must answer:
   - *"What valuable empirical facts or clues did the peer uncover?"*
   - *"What complementary papers, mathematical techniques, or data representations can expand their findings?"*
   - *"How can their conceptual hypotheses be converted into concrete, falsifiable experiments?"*
4. **Relay Output Contract:** `research/discoveries/relay_<agent_id>.md`.

### Pillar 4: Formal Experiment Planning (How Experiments Are Structured)
1. **Falsifiable Hypothesis Schema:** No experiment may be executed without a formal entry in `research/hypotheses.md` conforming to:
   - `ID`: e.g., `HYP-001`
   - `Statement`: Precise prediction of cause and effect (e.g., "Adding target encoding with smoothing $m=10.0$ improves validation AUC over frequency encoding").
   - `Theoretical Justification`: Why the change should improve performance or generalization.
   - `Intervention / Parameter Delta`: Exact git diff or configuration parameter change.
   - `Falsification Boundary`: Specific metric threshold below which the hypothesis is rejected (e.g., $\Delta \text{AUC} \le 0.0005$ or increased CV variance $> 0.02$).
   - `Expected Information Gain`: What we learn whether it succeeds or fails.
2. **Experiment Queue:** Planned experiments are registered in `planning/experiment_queue.json`.

### Pillar 5: Continuous Execution & Benchmarking (How Experiments Are Run)
1. **Leak-Free Cross-Validation:**
   - Preprocessing, target encoding, scaling, and feature selection MUST fit only on the training fold during each CV split.
   - Leakage prevention is verified via automated assertions.
2. **Out-of-Fold (OOF) Prediction Persistence:**
   - All models must output out-of-fold predictions saved to disk (`predictions/oof_<exp_id>.parquet` or `.csv`).
   - OOF predictions enable honest local evaluation, stacking, and metric audits without test-set feedback loops.
3. **Benchmarking & Logging:**
   - Raw logs saved to `experiments/experiment_log.md`.
   - Ranked summary saved to `experiments/local_leaderboard.md` tracking: `Exp ID`, `Hypothesis ID`, `CV Metric (Mean ± Std)`, `Baseline Delta`, `Runtime`, `Seed`, `Commit Hash`.

### Pillar 6: Dual Findings Ledger (How Discoveries Are Preserved)
1. **Positive Invariants Ledger (`findings/positive_invariants.md`):**
   - Documents verified improvements that achieve statistical significance.
   - Serves as the foundation for subsequent compounding iterations.
2. **Negative Findings Graveyard (`findings/negative_findings.md`):**
   - **MANDATORY:** Every failed experiment, neutral result, or code error must be recorded immediately.
   - Fields required:
     * `Experiment ID & Date`
     * `Tested Hypothesis`
     * `Observed Outcome vs Expected Outcome`
     * `Root Cause Analysis` (e.g., high cardinality leakage, gradient saturation, feature correlation)
     * `Permanent Negative Rule` (e.g., "Do NOT use unregularized target encoding on category X").
   - This prevents agent memory decay from cycling through previously failed ideas.

### Pillar 7: Independent Verification (How Claims Are Validated)
1. **Adversarial Skepticism:** The Verifier role must be decoupled from the Experimenter (different prompt persona, separate subagent, or fresh execution context).
2. **Verification Protocol:**
   - **Artifact Presence:** Verify that executable code, output logs, and OOF prediction files exist on disk.
   - **Hash Integrity:** Verify SHA-256 hashes of datasets and prediction matrices.
   - **Independent Metric Computation:** Verifier runs a standalone validation script that loads ground truth labels and OOF predictions, re-calculating the metric independently without relying on the experimenter's printed output.
   - **Cross-Validation Leakage Audit:** Verify split definitions, fold indices, and lack of test leakage.
3. **Evidence Record:** All verification outputs are logged in `verification/evidence.md` with explicit PASS/FAIL verdicts.

### Pillar 8: Continuation, Pivot & Stopping Rules (How Systems Decide)
1. **Continuation Gating:**
   - An experiment cycle cannot advance to the next phase if independent verification fails or is incomplete.
2. **Objective Stopping Conditions:**
   - **Resource / Iteration Budget:** Session stops when max iteration limit $N$ or allocated time budget is reached.
   - **Plateau Rule (Diminishing Returns):** If $K=3$ consecutive experiments produce metric gains below threshold ($\Delta < 0.001$), execution halts to prevent overfitting to validation folds.
   - **Target Met:** Execution stops when predefined benchmark criteria are met.
3. **Pivoting Rules:**
   - If consecutive experiments on a specific approach fail ($\ge 3$ consecutive failures or failure rate $> 60\%$), the protocol enforces a **Paradigm Pivot**: the agent is prohibited from minor hyperparameter tweaks and must pivot to an unexplored hypothesis category (e.g., error analysis, loss reformulation, or alternative representations).
4. **Audit Trail:** Decisions are recorded in `planning/next_actions.md` and machine-readable `state.json`.

---

## 3. Directory Layout for Protocol-Compliant Research

```
research_workspace/
├── objective.md
├── state.json
├── research/
│   ├── sources.md
│   ├── hypotheses.md
│   └── discoveries/
│       ├── discovery_<agent_A>.md
│       ├── discovery_<agent_B>.md
│       ├── relay_<agent_A>.md
│       └── relay_<agent_B>.md
├── experiments/
│   ├── experiment_log.md
│   └── local_leaderboard.md
├── findings/
│   ├── positive_invariants.md
│   └── negative_findings.md
├── predictions/
│   └── oof_<exp_id>.parquet
├── verification/
│   ├── evidence.md
│   └── verify_metrics.py
└── planning/
    ├── experiment_queue.json
    └── next_actions.md
```
