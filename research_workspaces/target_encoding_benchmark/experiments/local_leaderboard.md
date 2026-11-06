# Local Leaderboard: Top Verified Candidates

*Ranked top models / configurations verified through leak-free local 5-fold cross-validation.*

| Rank | Exp ID | Model / Solution Architecture | 5-Fold OOF Validation AUC (Mean ± Std) | In-Sample Diagnostic Gap (Train - Val) | Artifact Hashes | Verified By | Status |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---|
| **1** | **EXP_002** | **M-OOF Target Encoding (Optimal $m=10.0$)** | **0.69815 ± 0.01394 AUC** | **0.05352** | `ce4a5d18bd...` (`oof_predictions_exp002.pkl`) | kiza / kreten | Active Performance Champion (Nested CV: 0.69796 ± 0.01377) |
| 2 | EXP_001 | M-OOF Target Encoding ($m=10$) | 0.69810 ± 0.01410 AUC | 0.05410 | `3acaa9ed...` (`oof_predictions.pkl`) | kreten | Verified Candidate |
| 3 | EXP_002 | M-OOF Target Encoding ($m=20.0$) | 0.69752 ± 0.01400 AUC | 0.04845 | `ce4a5d18bd...` | kiza | Viable Alternative |
| 4 | EXP_002 | M-OOF Target Encoding ($m=5.0$) | 0.69712 ± 0.01465 AUC | 0.05946 | `ce4a5d18bd...` | kiza | Viable Alternative |
| 5 | EXP_001 | MB-OOF Target Encoding ($k=10, f=1$) | 0.69380 ± 0.01480 AUC | 0.05820 | `3acaa9ed...` | kreten | Verified Candidate |
| 6 | EXP_002 | M-OOF Target Encoding ($m=1000.0$) | 0.68960 ± **0.01303** AUC | **0.03763** | `ce4a5d18bd...` | kreten | Stability Champion (Lowest Fold Std Dev) |
| 7 | EXP_001 / EXP_002 | Raw Unregularized OOF Target Encoding ($m=0$) | 0.68707 ± 0.01560 AUC | 0.07531 | `ce4a5d18bd...` | kreten | Leak-Free Baseline |

---

### Scope & Evaluation Notice:
- **CV vs Test Performance:** All metrics reported above are derived from 5-Fold Stratified Out-of-Fold Cross-Validation on the training distribution. No external held-out test dataset was evaluated.
- **In-Sample Diagnostic Gap vs True OOF:** The gap column is termed "In-Sample Diagnostic Gap" because `train_encoded` includes each training sample's own target in its fold-map aggregation (in-sample memorization), and represents a composite array overwritten across folds. It serves as an internal diagnostic of memorization pressure, not an out-of-fold generalization metric.
- **Nested Cross-Validation Validation:** Nested 5-outer × 3-inner CV independently confirmed the $m=10.0$ parameter region with Mean Test AUC = 0.69796 ± 0.01377, proving selection optimism is negligible (0.00019 AUC).
- **Performance vs Stability Trade-Off:** The peak performance champion is $m=10.0$ (AUC 0.69815), while the maximum stability champion across folds is $m=1000.0$ (fold std dev 0.01303, diagnostic gap 0.03763). Extreme regularization reduces fold-to-fold variance by over-smoothing toward the global mean, trading off discriminative power.
