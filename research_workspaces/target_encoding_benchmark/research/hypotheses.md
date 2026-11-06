# Research Hypotheses & Status

## Active & Validated Hypotheses

| Hypothesis ID | Statement & Expected Effect | Proposed by | Validation Test / Experiment ID | Status (`PROPOSED` / `IN_TESTING` / `CONFIRMED` / `REFUTED`) | Expected Information Gain / Feasibility | Evidence Reference |
|---------------|-----------------------------|-------------|---------------------------------|--------------------------------------------------------------|------------------------------------------|--------------------|
| HYP_001       | Out-of-Fold (OOF) target encoding eliminates optimism bias from naive in-sample leakage, while adding additive M-estimate or sigmoidal smoothing stabilizes variance in rare levels, yielding superior leak-free 5-fold CV validation AUC. | kreten (`relay_kreten.md`) | EXP_001 | CONFIRMED | High / High | `evidence.md` (AUD_001: Val AUC 0.6981 vs 0.6871 baseline, 0% leakage) |
| HYP_002       | M-Estimate smoothing parameter sensitivity exhibits an optimal interior peak along a logarithmic grid $m \in \{0, 0.1, 1, 10, 100, 1000\}$: small $m \to 0$ suffers high variance, large $m \to 1000$ over-shrinks to the global prior, and an intermediate $m \approx 10$ maximizes 5-fold CV out-of-fold validation AUC (mean 0.69815). | kiza (`relay_kiza.md`) | EXP_002 | CONFIRMED (Refined Scope) | High / High (1D grid evaluation) | `evidence.md` (AUD_002: Peak Val AUC 0.69815 at $m=10.0$; lowest fold std 0.01303 at $m=1000.0$) |
| HYP_003       | Tree-based gradient boosting models (GBDT) trained on regularized OOF target encodings exhibit higher gain when combined with target-encoded pairwise categorical interactions compared to single-feature encodings alone. | kreten (`relay_kreten.md`) | EXP_003 | PROPOSED | Med / Med | Queued for next milestone following AUD_002 verification |

## Falsified / Refuted Hypotheses
*Negative findings, refuted assumptions, and disproved claims are permanently recorded here to prevent duplicate failures.*

| Hypothesis ID | Statement | Why Refuted / Benchmark Result | Experiment ID |
|---------------|-----------|--------------------------------|---------------|
| HYP_000_REF   | Global (Naive) in-sample Target Encoding can be safely evaluated on full training sets without cross-validation if sample size $N > 5000$. | Refuted: Overfitting is driven by level cardinality and low per-level counts ($n_c < 5$), producing massive artificial AUC inflation (0.7545 vs 0.6871 true generalization). | EXP_001 (V1_Naive vs V2_OOF) |
| HYP_002_SUB   | Optimal cross-validation AUC ($m=10.0$) and minimum cross-fold variance coincide at the same regularization parameter $m$. | Refuted: Cross-fold standard deviation decreases monotonically from $m=0.0$ (std: 0.01560) to $m=1000.0$ (std: 0.01303). At $m=10.0$, fold std is 0.01394. The asymptote $m=1000.0$ achieves maximal stability by collapsing variance toward the global prior, at the cost of discriminative AUC (0.68960). | EXP_002 (M-Estimate Grid Sensitivity) |

---

### Methodological Scope Rules:
- **CV vs Test Performance Distinction:** All hypothesis validation metrics refer exclusively to Out-of-Fold (OOF) validation scores derived from 5-Fold Stratified Cross-Validation on the training distribution. No external test set was evaluated. Out-of-fold CV must not be claimed as external test generalization.
- **Empirical Fidelity:** Experimental metrics must be reported exactly as produced by reproducible scripts without alteration.
