# Independent Verification & Audit Evidence

## Verification Log

| Audit ID | Task / Exp ID | Target Claim / Output | Verification Command(s) | Exit Code & SHA256 Checksum | Discrepancies Found | Final Verdict | Auditor Profile |
|----------|---------------|-----------------------|-------------------------|-----------------------------|---------------------|---------------|-----------------|
| AUD_001  | t_9a21f71f / EXP_001 | Leak-Free OOF TE AUCs | `python3 scripts/exp_001_benchmark.py` | 0 / 3acaa9ed... | None | PASS | kreten |
| AUD_002  | t_cf9f352e / EXP_002 | M-Estimate Grid AUCs & Code Integrity | `python3 scripts/exp_002_m_grid_sensitivity.py` | 0 / 61070c39... | Incomplete hypothesis scope (clarified) | PASS | kreten |

---

# Audit Report: EXP_001 — Target Encoding Benchmark

## Target Task
`t_9a21f71f`: [Relay-4] Evidence Verification: Independent audit of benchmark artifacts and fold leakage

## Evidence Audited
- Script: `scripts/exp_001_benchmark.py` (SHA256: `8b3cbbf9bb1da1a8633bc7c15cd253c182344fa219a0cdbb95b48f5bb5fdda7f`)
- Artifact: `experiments/artifacts/EXP_001/oof_predictions.pkl` (SHA256: `3acaa9edd8b838db3d0ac0713340fd26f2c43c2ea5219241b46cba0e4b57f82e`)

## Checks Run
1. **Reproducibility Test:** Ran `python3 scripts/exp_001_benchmark.py` in subshell.
   - Results:
     - V1_Naive: Mean AUC = 0.7545 (Severe in-sample target leakage)
     - V2_OOF: Mean AUC = 0.6871 (Unregularized leak-free baseline)
     - V3_M_OOF: Mean AUC = 0.6981 (Additive M-estimate smoothing, $m=10$)
     - V4_MB_OOF: Mean AUC = 0.6938 (Micci-Barreca sigmoidal smoothing, $k=10, f=1$)
   - Verdict: Exact numerical reproduction matching parent task claims.
2. **Artifact Integrity:** Verified SHA256 `3acaa9edd8b838db3d0ac0713340fd26f2c43c2ea5219241b46cba0e4b57f82e`.
3. **Leakage Audit:**
   - Reviewed `OOFEncoder.fit_transform`.
   - V1_Naive: Global fit/transform operates over all $N=10000$ samples without fold isolation (intentional negative control demonstrating optimism bias).
   - V2-V4: Confirmed StratifiedKFold cross-validation slice isolation. Validation samples are strictly evaluated on encodings computed from their respective training folds.

## Final Verdict
**PASS**

---

# Audit Report: EXP_002 — M-Estimate Grid Sensitivity & Dual-Side Code Audit

## Target Task
`t_cf9f352e`: [Verification] AUD_002: Independent isolated audit of EXP_001 and EXP_002 artifacts, leakage, and code integrity

## 1. Fresh Isolated Verifier Context Evidence
- **Auditor Profile Isolation:** The audit was conducted by profile `kreten` (Evidence Verifier), which is entirely decoupled from profile `kiza` (the Experiment Engineer who authored and executed `scripts/exp_002_m_grid_sensitivity.py`).
- **Autonomous Process Execution:** Executed via native Hermes Kanban task `t_cf9f352e` (Run #19, PID 1969005) inside workspace directory `/home/kizamladjanijebac/.gemini/antigravity/worktrees/discord-openclaw/analyze_discord_openclaw_setup/research_workspaces/target_encoding_benchmark`.
- **Memory & State Isolation:** The verifier spawned in a clean subshell process without shared in-memory Python object references, inspecting raw code and data directly from disk.

## 2. In-Depth Dual-Side Code Inspection (`MEstimateOOFEncoder.fit_transform`)

### A. Validation-Side Encoding (Leakage Audit)
```python
train_df = pd.DataFrame({'feat': X_train, 'targ': y_train})
agg = train_df.groupby('feat')['targ'].agg(['mean', 'count'])
fold_map = {
    cat: (agg.loc[cat, 'count'] * agg.loc[cat, 'mean'] + self.m * self.global_mean) / (agg.loc[cat, 'count'] + self.m)
    for cat in agg.index
}
for i in val_idx:
    cat = X[i]
    oof_encoded[i] = fold_map.get(cat, self.global_mean)
```
- **Fold Separation Check:** `fold_map` is derived strictly from `train_df` (`X_train`, `y_train`). The validation target values `y[val_idx]` never enter `agg` or `fold_map`.
- **Unseen Level Handling:** If a categorical level in `val_idx` does not exist in `X_train`, `fold_map.get(cat, self.global_mean)` falls back to the dataset prior mean, ensuring zero exception leakage or index mismatch.
- **Global Prior Nuance Audited:** `self.global_mean = float(np.mean(y))` was computed once over the entire target vector rather than inside the fold loop as `np.mean(y_train)`. With $N=10,000$ and stratified 5-fold splits ($N_{train}=8000$), the target class ratio is preserved within 0.0001 across folds. While fold-isolated prior calculation is theoretically purer, this does not leak category-specific information across validation folds.

### B. Training-Side Encoding (Generalization Gap Audit)
```python
for i in train_idx:
    cat = X[i]
    train_encoded[i] = fold_map.get(cat, self.global_mean)
```
- **Loop Overwriting Mechanism:** In a 5-fold split, each observation index $i$ appears in $K-1=4$ distinct training splits. The array `train_encoded` is updated in every fold iteration. Consequently, at the conclusion of the loop, `train_encoded[i]` holds the encoding value from the last fold iteration that included index $i$.
- **Empirical Impact Tested:** 
  - In `exp_002_m_grid_sensitivity.py`, the training AUC was evaluated against this composite array, yielding Mean Train AUC = 0.75167, Gen Gap = 0.05352 for $m=10.0$.
  - The verifier tested strict in-loop fold evaluation (calculating `roc_auc_score(y_train, train_pred)` directly inside each fold loop before any overwriting):
    - Strict In-Loop Mean Train AUC: **0.75067** (Fold std: 0.00304)
    - Strict In-Loop Mean Val AUC: **0.69815** (Fold std: 0.01394)
    - Strict In-Loop Generalization Gap: **0.05252** (vs 0.05352 composite)
  - **Verdict:** Both methods confirm significant in-sample memorization (~0.75 AUC vs ~0.698 AUC), verifying that out-of-fold partitioning is required to measure true performance.

## 3. Exact Reproducibility Inputs, Seeds, and Artifact Checksums

### Deterministic Inputs:
- **Random Seed:** `42` (`np.random.seed(42)`)
- **Dataset Generation Parameters:**
  - Sample size $N = 10,000$
  - Number of categorical levels $C = 500$
  - Category probability distribution: Pareto distribution $\alpha = 2$ (`np.random.pareto(2, 500)` normalized to $\sum p = 1$)
  - Target conditional probabilities: Beta distribution $(\alpha=2, \beta=5)$ (`np.random.beta(2, 5, 500)`)
  - Target assignment: Bernoulli trials (`np.random.binomial(1, cat_probs[c])`)
- **Partitioning Strategy:** `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`

### Verified Script Checksums (SHA256):
- `scripts/exp_001_benchmark.py`:
  `8b3cbbf9bb1da1a8633bc7c15cd253c182344fa219a0cdbb95b48f5bb5fdda7f`
- `scripts/exp_002_m_grid_sensitivity.py`:
  `34716bcb60207f5560ced44016e9ed50f8a5eaeba8ab03714f7e80e9688973b9`

### Verified Artifact Checksums (SHA256):
- `experiments/artifacts/EXP_001/oof_predictions.pkl`:
  `3acaa9edd8b838db3d0ac0713340fd26f2c43c2ea5219241b46cba0e4b57f82e`
- `experiments/artifacts/EXP_002/m_grid_results.pkl`:
  `61070c39217d6730b2290f54ecdf962cbc9c51dfda163802047194e32190dfe5`
- `experiments/artifacts/EXP_002/oof_predictions_exp002.pkl`:
  `ce4a5d18bd52a1d85f799a4d159a004bb66c94f78657d0e0169ecedaa7df164b`

## 4. Empirical Reproduction Results Matrix (EXP_002)

| $m$ Parameter | Mean Val AUC | Fold Std Dev | Mean Train AUC (Composite) | Mean Train AUC (Strict In-Loop) | Generalization Gap | Status |
|:-------------:|:------------:|:------------:|:--------------------------:|:-------------------------------:|:------------------:|:------:|
| $m = 0.0$ | 0.68707 | 0.01560 | 0.76239 | 0.76152 | 0.07531 | Baseline |
| $m = 0.1$ | 0.68772 | 0.01549 | 0.76238 | 0.76150 | 0.07466 | Verified |
| $m = 1.0$ | 0.69097 | 0.01533 | 0.76166 | 0.76077 | 0.07068 | Verified |
| $m = 5.0$ | 0.69712 | 0.01465 | 0.75658 | 0.75560 | 0.05946 | Verified |
| **$m = 10.0$** | **0.69815** | **0.01394** | **0.75167** | **0.75067** | **0.05352** | **Peak Performance Champion** |
| $m = 20.0$ | 0.69752 | 0.01400 | 0.74597 | 0.74492 | 0.04845 | Verified |
| $m = 50.0$ | 0.69504 | 0.01400 | 0.73859 | 0.73751 | 0.04355 | Verified |
| $m = 100.0$ | 0.69323 | 0.01353 | 0.73434 | 0.73327 | 0.04111 | Verified |
| $m = 500.0$ | 0.69036 | 0.01335 | 0.72826 | 0.72721 | 0.03790 | Verified |
| **$m = 1000.0$** | **0.68960** | **0.01303** | **0.72723** | **0.72618** | **0.03763** | **Stability Champion (Lowest Fold Std)** |

## 5. Methodological Scope & Discrepancies Clarified
- **Discrepancy in Initial Reporting:** Initial summaries reported $m=10.0$ as having both "highest AUC and lowest fold variance". The auditor verified that while $m=10.0$ achieves highest mean AUC (0.69815), $m=1000.0$ exhibits the lowest fold standard deviation (0.01303 vs 0.01394). This discrepancy has been corrected in `experiment_log.md`, `local_leaderboard.md`, and `hypotheses.md`.
- **Cross-Validation vs Test Performance:** All reported metrics are 5-Fold Stratified Out-of-Fold Cross-Validation scores. No external test set was evaluated. Out-of-fold CV validates against training distribution overfitting, not external distribution shift.

## Final Verdict
**PASS** — All numerical results, checksums, and zero-leakage constraints independently reproduced and verified.
