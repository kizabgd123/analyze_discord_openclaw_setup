# Research Extension: Target Encoding Regularization Analysis
Researcher: kiza
Reference: [kreten_discoveries.md]
Task: [Relay-Reciprocal-A]

## 1. M-Estimate Parameter Sensitivity Analysis
The M-Estimate formula $M_i = \frac{n_i \cdot \mu_i + m \cdot \mu_{global}}{n_i + m}$ represents a weighted average between the category evidence and the global prior. The sensitivity of the encoded value to the regularization parameter $m$ varies inversely with the sample size $n_i$.

### Sensitivity Dynamics
- **Low-Count Regime ($n_i \ll m$):** The encoding is highly sensitive to $m$. In this regime, $M_i \approx \mu_{global}$. The regularization dominates, effectively treating the category as "unreliable" and shrinking it toward the global average.
- **High-Count Regime ($n_i \gg m$):** The encoding is insensitive to $m$. $M_i \approx \mu_i$. The category evidence outweighs the prior, and the regularization has negligible impact.
- **Critical Transition Point ($n_i \approx m$):** This is the point of maximum uncertainty where the category mean and global mean are weighted equally.

### Asymptotic Behavior
- **When $m = 0$:** The estimate reduces to the Naive Target Encoder ($M_i = \mu_i$), maximizing variance and overfitting risk for rare categories.
- **When $m \to \infty$:** The estimate converges to the global mean ($\mu_{global}$), eliminating all category-specific information (maximum bias, zero variance).

---

## 2. Cross-Validation Complexity & Tuning Overhead
Tuning regularization parameters introduces a significant risk of **Tuning Leakage** if not handled via rigorous Out-Of-Fold (OOF) protocols.

### Computational Complexity
- **M-Estimate:** Requires a 1D grid search over $m$. The complexity is $O(G \cdot N)$ where $G$ is the grid size and $N$ is the number of observations.
- **Micci-Barreca:** Requires a 2D grid search over $k$ and $f$. The complexity grows quadratically with the search space ($O(G_k \cdot G_f \cdot N)$), making it significantly more expensive to optimize.

### The Validation Bottleneck
To find the optimal $m$ without leaking the target, one must:
1. Split data into $K$ folds.
2. For each value in the grid:
   - Compute OOF encodings for all folds.
   - Evaluate a downstream model (e.g., Logistic Regression) on the OOF predictions.
   - Record the validation metric.
3. Select the $m$ that maximizes the OOF metric.

The total complexity is $O(K \cdot G \cdot N)$. For high-cardinality features, the iterative nature of this process becomes a primary bottleneck in the feature engineering pipeline.

---

## 3. Proposed Parameter Grid for HYP_002
To validate the hypothesis that M-Estimate is easier to tune and potentially more robust for high-cardinality data, I propose the following experimental setup for **HYP_002**.

### Goal
Determine the optimal smoothing strength $m$ that minimizes OOF LogLoss/maximizes AUC across diverse cardinality distributions.

### Proposed M-Estimate Grid (Logarithmic Scale)
Given that the effect of $m$ is relative to $n_i$, a logarithmic grid is more efficient than a linear one:
$$m \in \{0, 0.1, 1, 10, 100, 1000\}$$

### Comparison Baseline (Micci-Barreca)
To provide a fair comparison, the Micci-Barreca search space should be constrained to a similar total number of evaluations (6 combinations):
- $k \in \{10, 100\}$
- $f \in \{1, 10, 50\}$ (adjusted to match the total 6-point evaluation budget)

### Evaluation Metric
The primary metric will be the **OOF Generalization Gap**:
$$\text{Gap} = \text{Metric}_{\text{train}} - \text{Metric}_{\text{OOF}}$$
The optimal parameter is the one that minimizes this gap while maintaining high absolute performance.
