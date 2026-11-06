# Research Discoveries: Regularization for Target Encoding
Researcher: kreten
Task: [Relay-1B] Independent Discovery

## Executive Summary
Target encoding of high-cardinality categorical features is prone to overfitting, especially for rare categories (low sample size). Regularization techniques mitigate this by shrinking the category-specific target mean toward the global target mean. The two primary methods investigated are Micci-Barreca Smoothing and M-Estimate (Additive Smoothing).

## Empirical Evidence & Discoveries

### 1. Micci-Barreca Smoothing
This method uses a weight factor based on a sigmoidal function to blend the category mean with the global mean.

**[FACT] Formula:**
The encoded value $S_i$ for category $i$ is:
$$S_i = \lambda(n_i) \cdot \mu_i + (1 - \lambda(n_i)) \cdot \mu_{global}$$

Where:
- $n_i$: Number of observations in category $i$.
- $\mu_i$: Mean target value for category $i$.
- $\mu_{global}$: Global mean target value across all observations.
- $\lambda(n_i)$: The weight factor, typically defined as:
$$\lambda(n_i) = \frac{1}{1 + \exp\left(-\frac{n_i - k}{f}\right)}$$

**[FACT] Hyperparameters:**
- $k$ (`min_samples_leaf`): The inflection point of the sigmoid. When $n_i = k$, $\lambda = 0.5$.
- $f$ (`smoothing`): Controls the slope of the transition. A larger $f$ makes the transition from global mean to category mean more gradual.

**[FACT] Behavior:**
- For $n_i \ll k$, $\lambda \to 0$, and the encoding is dominated by the global mean $\mu_{global}$.
- For $n_i \gg k$, $\lambda \to 1$, and the encoding is dominated by the category mean $\mu_i$.

### 2. M-Estimate (Additive Smoothing)
A simpler linear shrinkage method that adds "pseudo-observations" to the category count.

**[FACT] Formula:**
The encoded value $M_i$ for category $i$ is:
$$M_i = \frac{n_i \cdot \mu_i + m \cdot \mu_{global}}{n_i + m}$$
Alternatively expressed as:
$$M_i = \frac{\sum(y_{i}) + m \cdot \mu_{global}}{n_i + m}$$

Where:
- $n_i$: Number of observations in category $i$.
- $\mu_i$: Mean target value for category $i$.
- $\mu_{global}$: Global mean target value.
- $m$: Regularization parameter.

**[FACT] Behavior:**
- $m$ acts as the weight of the prior. A higher $m$ results in stronger shrinkage toward the global mean.
- Unlike Micci-Barreca, the weighting is linear rather than sigmoidal.

## Verified Sources & References
- Micci-Barreca, Daniele. "A preprocessing scheme for high-cardinality categorical attributes in classification and prediction problems."
- Scikit-learn implementation: `sklearn.preprocessing._target_encoder_fast.pyx` (uses Micci-Barreca Eq 7).
- Category Encoders library: `category_encoders.m_estimate.MEstimateEncoder`.
- Dataiku DSS Documentation: Impact Coding (M-estimator).

## Testable Hypotheses
**[HYPOTHESIS]:** On datasets with extremely high cardinality (where many categories have $n_i < 5$), M-Estimate will be easier to tune than Micci-Barreca because it only requires one hyperparameter ($m$) versus two ($k, f$).
- **Validation:** Compare RMSE/LogLoss of a model using M-Estimate vs Micci-Barreca across a grid search of hyperparameters on a high-cardinality synthetic dataset.

**[HYPOTHESIS]:** Micci-Barreca smoothing will outperform M-Estimate when there is a clear threshold of "reliability" for category counts (e.g., categories with $< 10$ samples are noise, but $> 10$ are highly reliable).
- **Validation:** Test on a dataset where a known threshold exists; the sigmoidal transition of Micci-Barreca should capture this better than linear shrinkage.

## Failed Attempts & Negative Findings
- None.

## Open Questions & High-Value Next Leads
- How does "Ordered Target Encoding" (streaming approach) interact with these smoothing methods to further prevent target leakage?
- Would hierarchical smoothing (shrinking toward a parent group mean instead of global mean) provide a significant boost for structured categories (e.g., ZIP codes)?
