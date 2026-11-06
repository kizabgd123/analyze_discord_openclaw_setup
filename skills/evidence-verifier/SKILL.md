---
name: evidence-verifier
description: Skeptical independent verification skill. Audits experimental artifacts, validates checksums, independently recomputes metrics, and inspects cross-validation splits for leakage.
---

# Evidence Verifier Protocol

## Mission
Provide rigorous, skeptical, and independent verification of experimental claims. The verifier never assumes an experiment succeeded because an agent claimed so. It validates tangible evidence on disk, verifies checksums, independently runs verification code, and guards against data leakage.

## Verification Checklist

1. **Artifact Verification:**
   - Verify that the experiment script exists and runs without interactive flags.
   - Verify that out-of-fold predictions exist on disk (`predictions/oof_<exp_id>.parquet` or `.csv`).
   - Check file sizes and line/row counts to ensure no silent truncation occurred.

2. **Integrity & Checksum Audit:**
   - Compute SHA-256 hashes of input datasets, split indices, and prediction files.
   - Ensure predictions are not constant, NaN-filled, or trivially degenerate.

3. **Independent Metric Recomputation:**
   - Load ground truth target labels directly from raw source.
   - Load OOF prediction array independently.
   - Execute a standalone metric calculation function.
   - Compare the independently computed metric against the claimed score in `local_leaderboard.md`. Any discrepancy $> 10^{-5}$ results in an immediate FAIL.

4. **Leakage & CV Integrity Audit:**
   - Inspect split logic: verify no overlapping sample indices between train and test folds.
   - For time-series data: verify no future information is present in past training windows.
   - For grouped data: verify group disjointness across folds.

5. **Verdict & Evidence Logging:**
   - Record comprehensive findings in `verification/evidence.md`:
     * Timestamp
     * Experiment ID verified
     * Claimed Score vs Verified Score
     * SHA-256 Hashes
     * Leakage Audit Result (PASS/FAIL)
     * Overall Verdict: **PASSED** | **BLOCKED**
