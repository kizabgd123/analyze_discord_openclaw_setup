# Research Hypotheses & Status

## Active & Validated Hypotheses

| Hypothesis ID | Statement & Expected Effect | Proposed by | Validation Test / Experiment ID | Status (`PROPOSED` / `IN_TESTING` / `CONFIRMED` / `REFUTED`) | Expected Information Gain / Feasibility | Evidence Reference |
|---------------|-----------------------------|-------------|---------------------------------|--------------------------------------------------------------|------------------------------------------|--------------------|
| HYP_001       | Out-of-Fold (OOF) target encoding eliminates optimism bias from naive in-sample leakage, while adding additive M-estimate or sigmoidal smoothing stabilizes variance in rare levels, yielding superior leak-free validation AUC. | kreten (`relay_kreten.md`) | EXP_001 | CONFIRMED | High / High | `evidence.md` (AUC: 0.6981 vs 0.6871, 0% leakage) |
| HYP_002       | M-Estimate smoothing parameter sensitivity exhibits an optimal interior peak along a logarithmic grid $m \in \{0, 0.1, 1, 10, 100, 1000\}$: small $m \to 0$ suffers high variance, large $m \to 1000$ over-shrinks to the global prior, and an intermediate $m \approx 10$ maximizes OOF test AUC. | kiza (`relay_kiza.md`) | EXP_002 | IN_TESTING | High / High (1D grid evaluation) | `exp_002_m_grid_sensitivity.py` |
| HYP_003       | Tree-based gradient boosting models (GBDT) trained on regularized OOF target encodings exhibit higher gain when combined with target-encoded pairwise categorical interactions compared to single-feature encodings alone. | kreten (`relay_kreten.md`) | EXP_003 | PROPOSED | Med / Med | Awaiting EXP_002 verification |

## Falsified / Refuted Hypotheses
*Negative findings and disproved assumptions are permanently recorded here to prevent duplicate failures.*

| Hypothesis ID | Statement | Why Refuted / Benchmark Result | Experiment ID |
|---------------|-----------|--------------------------------|---------------|
| HYP_000_REF   | Global (Naive) in-sample Target Encoding can be safely evaluated on full training sets without cross-validation if sample size $N > 5000$. | Refuted: Overfitting is driven by level cardinality and low per-level counts ($n_c < 5$), producing massive artificial AUC inflation (0.7545 vs 0.6871 true generalization). | EXP_001 (V1_Naive vs V2_OOF) |
