---
name: experiment-runner
description: Continuous experiment execution and benchmarking skill. Manages leak-free cross-validation, out-of-fold prediction persistence, real-time logging, and local leaderboard tracking.
---

# Experiment Runner & Benchmarking Protocol

## Overview
This skill executes empirical experiments derived from formal hypotheses. It enforces leakage-free validation, out-of-fold (OOF) prediction persistence, and systematic recording in the project's local leaderboard.

## Execution Rules

1. **Pre-Execution Check:**
   - Ingest `planning/experiment_queue.json` and verify `research/hypotheses.md`.
   - Check `findings/negative_findings.md` to ensure the planned experiment does not duplicate a previously failed attempt.

2. **Leak-Free Cross-Validation:**
   - Enforce strict separation between train and validation folds.
   - All transformations (imputation, scaling, target encoding, feature selection) MUST be fitted strictly on the training folds.
   - Maintain deterministic random seeds across folds.

3. **Out-of-Fold (OOF) Prediction Persistence:**
   - Generate OOF predictions for the entire training set.
   - Save directly to disk: `predictions/oof_<exp_id>.parquet` or `.csv`.
   - Never overwrite previous experiment predictions.

4. **Logging & Leaderboard Update:**
   - Append raw execution details, hardware specs, and runtime to `experiments/experiment_log.md`.
   - Update `experiments/local_leaderboard.md` with:
     * Rank
     * Experiment ID
     * Hypothesis ID
     * Metric Score (Mean ± Std across folds)
     * Baseline $\Delta$
     * Commit Hash / Script Path

5. **Ledger Update:**
   - If metric improves and passes significance: log preliminary findings to `findings/positive_invariants.md`.
   - If metric regresses, is neutral, or code errors: MANDATORY logging to `findings/negative_findings.md` detailing root cause.
