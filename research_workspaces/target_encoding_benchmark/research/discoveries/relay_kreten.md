# Research Relay Extension: Unified Target Encoding Framework
Researcher: kreten
Peer Source: kiza_discoveries.md
Relay Task: [Relay-2]

## 1. Peer Clues Utilized
- **Leakage Mechanism (Kiza):** Confirmed that Naive TE leads to "optimism bias" because the row's own target is in the mean.
- **OOF Logic (Kiza):** OOF encoding via $K$-fold partitioning effectively decouples the row from its encoding source.
- **Smoothing Necessity (Kiza):** High-cardinality features with $n_c < 5$ require blending with the global mean to avoid high variance.
- **Regularization Math (Kreten):** Micci-Barreca (sigmoidal) and M-Estimate (linear) provide the precise mechanisms for this blending.

## 2. Synthesized Insights
Target Encoding is a two-dimensional optimization problem: **Leakage Control** (Temporal/Spatial) and **Variance Control** (Statistical). 

- **OOF partitioning** handles the Leakage dimension.
- **Smoothing/Regularization** handles the Variance dimension.

Neither is sufficient on its own for production-grade high-cardinality features. OOF without smoothing still overfits rare categories (though it doesn't "leak" in the naive sense). Smoothing without OOF still leaks the target value. The synthesis is a **Regularized OOF Framework**.

## 3. Refined Hypothesis (HYP_001)
**Statement:** For categorical features with high cardinality and skewed category distributions, the combination of Out-of-Fold (OOF) partitioning and Micci-Barreca smoothing will yield the lowest Generalization Gap (Train-Val Delta) and highest Validation Stability compared to Naive TE and unsmoothed OOF TE.

**Falsification Condition:** If OOF Target Encoding without smoothing performs equally or better on validation sets for rare categories ($n_c < 10$), the "Smoothing" component of the hypothesis is refuted.

## 4. Concrete Experiment Proposal: `EXP_TE_BENCHMARK_01`

### Configuration Matrix
| Variant | Partitioning | Regularization | Expected Behavior |
|----------|-------------|----------------|-------------------|
| V1: Naive | None        | None           | Massive Overfit (Low Train Error, High Val Error) |
| V2: OOF   | K-Fold      | None           | Leakage Fixed, but Rare Cat Variance High |
| V3: M-OOF | K-Fold      | M-Estimate     | Stable, Linear Shrinkage |
| V4: MB-OOF| K-Fold      | Micci-Barreca  | Stable, Sigmoidal (Non-linear) Shrinkage |

### Parameters
- **K-Folds:** 5
- **M-Estimate $m$:** Grid search $[1, 5, 10, 20]$
- **MB-Smoothing $k, f$:** Grid search $k \in [5, 10, 20]$, $f \in [1, 5, 10]$
- **Metric:** Generalization Gap = $\text{RMSE}_{val} - \text{RMSE}_{train}$

## 5. Handoff Checklist for Experiment Engineer
- [ ] Generate synthetic dataset with:
    - Feature A: High cardinality, Power-law distribution of counts.
    - Target: Linear relationship with category means + Gaussian noise.
- [ ] Implement `OOFEncoder` class supporting both M-Estimate and Micci-Barreca logic.
- [ ] Run 5-fold CV across the Configuration Matrix.
- [ ] Plot "Category Count vs. Encoding Value" to visualize the shrinkage effect.
