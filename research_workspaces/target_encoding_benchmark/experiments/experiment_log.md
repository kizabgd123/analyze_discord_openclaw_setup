# Experiment Execution Log

*Every experiment executed must be recorded here regardless of outcome. Never erase failed runs.*

| Exp ID | Hypothesis ID | Description / Change Tested | Baseline Metric | Result Metric | Delta | Status (`SUCCESS` / `FAILED` / `CRASH`) | Artifact Paths | Decision (`KEEP` / `REJECT` / `INVESTIGATE`) |
|--------|---------------|-----------------------------|-----------------|---------------|-------|-----------------------------------------|----------------|----------------------------------------------|
| EXP_001 | HYP_001       | Leak-Free OOF Target Encoding (Naive vs OOF vs M-OOF vs MB-OOF) | N/A | V1: 0.7545, V2: 0.6871, V3: 0.6981, V4: 0.6938 (Mean AUC) | N/A | SUCCESS | `experiments/artifacts/EXP_001/oof_predictions.pkl` | KEEP |
| EXP_002 | HYP_002       | Parameter Sensitivity & Asymptotic Search of M-Estimate Smoothing across $m \in [0, 1000]$ (10 grid points, 5-fold CV) | V2_OOF: 0.68707 (Gen Gap: 0.07531) | Optimal $m=10.0$: Val AUC=0.69815 (Gen Gap: 0.05352); Asymptotic $m=1000$: Val AUC=0.68960 | $\Delta = +0.01108$ AUC vs unregularized; -0.02179 Gen Gap | SUCCESS | `experiments/artifacts/EXP_002/m_grid_results.pkl`, `experiments/artifacts/EXP_002/oof_predictions_exp002.pkl` | KEEP (Promoted to Leaderboard #1) |

## EXP_002 Detailed Sensitivity Matrix

| $m$ Parameter | Mean Val AUC | Fold Std Dev | Mean Train AUC | Generalization Gap ($\text{Train} - \text{Val}$) | Causal Behavior |
|---------------|--------------|--------------|----------------|--------------------------------------------------|-----------------|
| $m = 0.0$ | 0.68707 | 0.01560 | 0.76239 | 0.07531 | Unregularized OOF baseline (high variance on rare cats) |
| $m = 0.1$ | 0.68772 | 0.01549 | 0.76238 | 0.07466 | Negligible shrinkage |
| $m = 1.0$ | 0.69097 | 0.01533 | 0.76166 | 0.07068 | Mild variance reduction |
| $m = 5.0$ | 0.69712 | 0.01465 | 0.75658 | 0.05946 | Rapid generalization improvement |
| **$m = 10.0$** | **0.69815** | **0.01394** | **0.75167** | **0.05352** | **Optimal performance peak (highest mean Val AUC; intermediate fold std: 0.01394)** |
| $m = 20.0$ | 0.69752 | 0.01400 | 0.74597 | 0.04845 | Mild over-smoothing begins |
| $m = 50.0$ | 0.69504 | 0.01400 | 0.73859 | 0.04355 | Noticeable shrinkage toward global mean |
| $m = 100.0$ | 0.69323 | 0.01353 | 0.73434 | 0.04111 | Over-smoothing suppresses genuine category signal |
| $m = 500.0$ | 0.69036 | 0.01335 | 0.72826 | 0.03790 | Severe attenuation |
| **$m = 1000.0$** | **0.68960** | **0.01303** | **0.72723** | **0.03763** | **Asymptotic stability limit: lowest fold standard deviation (0.01303) and smallest generalization gap (0.03763), but reduced discriminative power** |

### Methodological & Empirical Notes:
1. **Bias-Variance & Stability Trade-off:**
   - $m = 10.0$ achieves the highest discriminative performance across the 5 validation folds (mean Val AUC = 0.69815).
   - $m = 1000.0$ achieves the highest stability across folds, demonstrating the lowest fold standard deviation (0.01303 vs 0.01394 for $m=10.0$) and the narrowest generalization gap (0.03763 vs 0.05352). Extreme shrinkage forces all category representations toward the uniform global prior $\mu_{global}$, which dampens fold-to-fold variance but erodes discriminative signal (AUC decreases by -0.00855 from the peak).
   - Hypotheses claiming that optimal AUC and minimal fold variance coincide at $m=10.0$ are empirically refuted by these results.
2. **Evaluation Scope: Cross-Validation vs External Test Performance:**
   - All validation metrics in this log represent Out-of-Fold (OOF) cross-validation evaluation under 5-Fold Stratified K-Fold.
   - No separate, held-out external test set was utilized in EXP_001 or EXP_002. These metrics measure out-of-fold generalization on the training distribution and must not be conflated with generalization to unseen future test distributions.

## SV1 Corrections — Scientific Validation Phase (2026-11-06)

### Train-Side `train_encoded` Terminology Correction
**Previous description:** "Mean Train AUC" implied out-of-fold training metric.
**Corrected description:** `train_encoded[i]` for training observations is an **in-sample composite diagnostic**, not an OOF metric. For each training row `i`, `fold_map` was computed from the fold where `i ∈ train_idx`, which includes `y[i]` itself in the groupby aggregation. The encoding therefore reflects the row's own target. The array is additionally overwritten 4 times per row (once per training fold), with the final value from the last applicable fold.

**Impact on reported metrics:**
- Val AUC figures (e.g. 0.69815 for m=10) are **unaffected** — they were always correctly out-of-fold.
- `mean_train_auc` (~0.75167) is an in-sample composite diagnostic metric, NOT a cross-validated training AUC.
- `generalization_gap` ≈ 0.05352 is derived from the in-sample train composite vs OOF val, making it an approximate gap diagnostic rather than a precisely defined statistical quantity.
- Both the composite (0.75167) and strict in-loop (0.75067) train AUC methods confirm strong in-sample memorization vs val AUC (~0.698). The directional conclusion (fold isolation is necessary) is unaffected.

### Nested CV Parameter Validation (SV1-P2)
**Method:** 5-outer × 3-inner nested CV, outer seed=42, inner seed=99.
**Result:** Nested CV Mean Test AUC = **0.69796 ± 0.01377**
**Selection bias vs flat 5-fold:** 0.69815 − 0.69796 = **0.00019** (< 0.03%, negligible)
**Best m across outer folds:** [10, 20, 10, 20, 10] → m ∈ {10, 20} robustly near-optimal.
**Conclusion:** m=10 is confirmed as a near-optimum by independent nested CV. The original flat 5-fold selection was technically evaluated on the same data used for selection, but the selection bias is negligible.
