# Independent Discovery: Leak-Free OOF Target Encoding Formulation

## Executive Summary
Target Encoding (TE) is a powerful method for handling high-cardinality categorical features by replacing labels with the mean of the target variable. However, **Naive Target Encoding** introduces severe target leakage because a row's own target value is used to calculate its feature, leading to overfitting and "optimism bias." **Out-of-Fold (OOF) Target Encoding** mitigates this by ensuring the encoding for any given row is derived only from other rows in the dataset. To further stabilize estimates for rare categories, **Smoothing** is applied to blend category means with the global target mean.

## Empirical Evidence & Discoveries

### 1. Naive Target Encoding [FACT]
In Naive TE, the categorical value $c$ is replaced by the average target value of all observations belonging to that category.

**Mathematical Formulation:**
$$TE(c) = \frac{1}{n_c} \sum_{i: x_i = c} y_i$$
Where:
- $n_c$: Number of rows in category $c$.
- $y_i$: Target value for row $i$.

**The Leakage Mechanism:**
For any row $i$ where $x_i = c$, the feature $TE(c)$ contains $y_i$ in its numerator. If $n_c$ is small (e.g., $n_c=1$), $TE(c)$ becomes exactly $y_i$, giving the model a direct path to the answer. This causes the model to rely on the encoded feature as a proxy for the target rather than learning the underlying relationship.

### 2. Out-of-Fold (OOF) Target Encoding [FACT]
OOF Encoding removes the current row (and its fold) from the mean calculation to prevent leakage.

**Implementation Logic:**
1. Split the training set into $K$ folds (e.g., 5-fold CV).
2. For all rows in $\text{Fold}_k$, calculate the category means using only data from $\text{Folds}_{j \neq k}$.
3. Map these means back to the rows in $\text{Fold}_k$.

**Mathematical Formulation (for row $i \in \text{Fold}_k$):**
$$TE_{OOF}(x_i = c) = \frac{\sum_{j \notin \text{Fold}_k, x_j = c} y_j}{\sum_{j \notin \text{Fold}_k, x_j = c} 1}$$

### 3. Target Smoothing [FACT]
To prevent "shaky" averages for categories with very few samples, the category mean is shrunk toward the global mean.

**Mathematical Formulation:**
$$TE_{smoothed}(c) = \lambda(n_c) \cdot \text{Mean}_c + (1 - \lambda(n_c)) \cdot \text{GlobalMean}$$
Where $\lambda(n_c)$ is a weighting factor (often a sigmoid function) that increases as $n_c$ grows, giving more weight to the category mean as evidence increases.

## Verified Sources & References
- **SRC_001:** r-statistics.co - Detailed breakdown of OOF and smoothing logic.
- **SRC_004:** Karpeles Guide - Quantifies the optimism bias (e.g., Naive CV estimate 0.846 vs New-Row score 0.733).

## Testable Hypotheses
- **[HYPOTHESIS 1]:** As the number of folds $K$ increases, the OOF encoding becomes a closer approximation of the Naive encoding, but the leakage risk remains constant (since the row is always excluded).
- **[HYPOTHESIS 2]:** In datasets with extremely high cardinality (where many categories have $n_c < 5$), smoothing will significantly reduce the variance of the OOF encoded feature and improve Generalization Error.

## Failed Attempts & Negative Findings
- **Single-row Leave-One-Out (LOO) vs K-Fold:** While LOO is the theoretical limit of OOF, in practice, K-Fold is preferred to avoid subtle leakage that can occur when the model is trained on LOO features within the same optimization loop.

## Open Questions & High-Value Next Leads
- **Dynamic Smoothing:** Would an adaptive smoothing parameter $\lambda$ (optimized via a small validation set) outperform a fixed sigmoid smoothing function?
- **Interaction with Gradient Boosting:** How does OOF Target Encoding interact with the internal binning logic of LightGBM/XGBoost?
