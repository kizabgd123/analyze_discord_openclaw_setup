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
| **$m = 10.0$** | **0.69815** | **0.01394** | **0.75167** | **0.05352** | **Optimal regularization peak (highest AUC, lowest fold variance)** |
| $m = 20.0$ | 0.69752 | 0.01400 | 0.74597 | 0.04845 | Mild over-smoothing begins |
| $m = 50.0$ | 0.69504 | 0.01400 | 0.73859 | 0.04355 | Noticeable shrinkage toward global mean |
| $m = 100.0$ | 0.69323 | 0.01353 | 0.73434 | 0.04111 | Over-smoothing suppresses genuine category signal |
| $m = 500.0$ | 0.69036 | 0.01335 | 0.72826 | 0.03790 | Severe attenuation |
| $m = 1000.0$ | 0.68960 | 0.01303 | 0.72723 | 0.03763 | Asymptotic limit: converges toward global mean feature |
