# Independent Verification & Audit Evidence

## Verification Log

| Audit ID | Task / Exp ID | Target Claim / Output | Verification Command(s) | Exit Code & SHA256 Checksum | Discrepancies Found | Final Verdict | Auditor Profile |
|----------|---------------|-----------------------|-------------------------|-----------------------------|---------------------|-------------------|------------------|
| AUD_001  | t_9a21f71f / EXP_001 | Leak-Free OOF TE AUCs | `python3 scripts/exp_001_benchmark.py` | 0 / 3acaa9ed... | None | PASS | kreten |
| AUD_002  | t_eb661e8b / EXP_002 | M-Estimate Grid AUCs | `python3 scripts/exp_002_m_grid_sensitivity.py` | 0 / 61070c39... | None | PASS | kreten |

---

# Audit Report: EXP_001 - Target Encoding Benchmark

## Target Task
t_9a21f71f: [Relay-4] Evidence Verification: Independent audit of benchmark artifacts and fold leakage

## Evidence Audited
- Script: `scripts/exp_001_benchmark.py`
- Artifact: `experiments/artifacts/EXP_001/oof_predictions.pkl`
- Execution Log: Reproduced in current session.

## Checks Run
1. **Reproducibility Test:** Ran `python3 scripts/exp_001_benchmark.py`.
   - Results:
     - V1_Naive: AUC=0.7545
     - V2_OOF: AUC=0.6871
     - V3_M_OOF: AUC=0.6981
     - V4_MB_OOF: AUC=0.6938
   - Verdict: Exact match with parent task claims.
2. **Artifact Integrity:**
   - SHA256: `3acaa9edd8b838db3d0ac0713340fd26f2c43c2ea5219241b46cba0e4b57f82e`
   - Status: Verified.
3. **Leakage Audit:**
   - Reviewed `OOFEncoder.fit_transform`.
   - V1_Naive: Confirmed global fit/transform (expected leakage).
   - V2-V4: Confirmed strict StratifiedKFold separation. Target values for validation samples are never used to compute the encoding for those same samples.
   - Verdict: No unintended target leakage in OOF variants.

## Discrepancies / Anomalies
None.

## Final Verdict
PASS

---

# Audit Report: EXP_002 - M-Estimate Grid Sensitivity

## Target Task
t_eb661e8b: [Verification] Independent audit of EXP_001 and EXP_002 artifacts

## Evidence Audited
- Script: `scripts/exp_002_m_grid_sensitivity.py`
- Artifacts: 
    - `experiments/artifacts/EXP_002/m_grid_results.pkl`
    - `experiments/artifacts/EXP_002/oof_predictions_exp002.pkl`
- Execution Log: Reproduced in current session.

## Checks Run
1. **Reproducibility Test:** Ran `python3 scripts/exp_002_m_grid_sensitivity.py`.
   - Results:
     - m=10.0: Val AUC=0.69815 (Optimal)
     - m=0.0: Val AUC=0.68707
     - Generalization Gap: Monotonically decreased from 0.0753 (m=0) to 0.0376 (m=1000).
   - Verdict: Exact match with parent task claims.
2. **Artifact Integrity:**
   - `m_grid_results.pkl` SHA256: `61070c39217d6730b2290f54ecdf962cbc9c51dfda163802047194e32190dfe5`
   - `oof_predictions_exp002.pkl` SHA256: `ce4a5d18bd52a1d85f799a4d159a004bb66c94f78657d0e0169ecedaa7df164b`
   - Status: Verified.
3. **Leakage Audit:**
   - Reviewed `MEstimateOOFEncoder.fit_transform`.
   - Confirmed strict StratifiedKFold separation. `fold_map` is computed using only `X_train` and `y_train`. Validation samples (`X_val`) are mapped using this `fold_map` without their own targets influencing the mean.
   - Verdict: 0% target leakage in validation folds.

## Discrepancies / Anomalies
None.

## Final Verdict
PASS
