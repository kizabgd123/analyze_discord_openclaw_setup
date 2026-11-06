# Local Leaderboard: Top Verified Candidates

*Ranked top models / configurations verified through leak-free local validation.*

| Rank | Exp ID | Model / Solution Architecture | Validation Metric (Mean ± Std) | Generalization Gap | Artifact Hashes | Verified By | Status |
|------|--------|-------------------------------|--------------------------------|--------------------|-----------------|-------------|--------|
| **1** | **EXP_002** | **M-OOF Target Encoding (Optimal $m=10.0$)** | **0.69815 ± 0.01394 AUC** | **0.05352** | `ce4a5d18bd...` (`oof_predictions_exp002.pkl`) | kiza / kreten | Active Champion |
| 2 | EXP_001 | M-OOF Target Encoding ($m=10$) | 0.69810 ± 0.01410 AUC | 0.05410 | `3acaa9ed...` (`oof_predictions.pkl`) | kreten | Verified Candidate |
| 3 | EXP_002 | M-OOF Target Encoding ($m=20.0$) | 0.69752 ± 0.01400 AUC | 0.04845 | `ce4a5d18bd...` | kiza | Viable Alternative |
| 4 | EXP_002 | M-OOF Target Encoding ($m=5.0$) | 0.69712 ± 0.01465 AUC | 0.05946 | `ce4a5d18bd...` | kiza | Viable Alternative |
| 5 | EXP_001 | MB-OOF Target Encoding ($k=10, f=1$) | 0.69380 ± 0.01480 AUC | 0.05820 | `3acaa9ed...` | kreten | Verified Candidate |
| 6 | EXP_001 / EXP_002 | Raw Unregularized OOF Target Encoding ($m=0$) | 0.68707 ± 0.01560 AUC | 0.07531 | `ce4a5d18bd...` | kreten | Leak-Free Baseline |
