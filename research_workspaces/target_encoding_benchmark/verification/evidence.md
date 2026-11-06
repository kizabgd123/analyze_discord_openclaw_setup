# Independent Verification & Audit Evidence

## Verification Log

| Audit ID | Task / Exp ID | Target Claim / Output | Verification Command(s) | Exit Code & SHA256 Checksum | Discrepancies Found | Final Verdict | Auditor Profile |
|----------|---------------|-----------------------|-------------------------|-----------------------------|---------------------|-------------------|------------------|
| AUD_001  | t_9a21f71f / EXP_001 | Leak-Free OOF TE AUCs | `python3 scripts/exp_001_benchmark.py` | 0 / 3acaa9ed... | None | PASS | kreten |

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
