# Experiment Execution Log

*Every experiment executed must be recorded here regardless of outcome. Never erase failed runs.*

| Exp ID | Hypothesis ID | Description / Change Tested | Baseline Metric | Result Metric | Delta | Status (`SUCCESS` / `FAILED` / `CRASH`) | Artifact Paths | Decision (`KEEP` / `REJECT` / `INVESTIGATE`) |
|--------|---------------|-----------------------------|-----------------|---------------|-------|-----------------------------------------|----------------|----------------------------------------------|
| EXP_001 | HYP_001       | Leak-Free OOF Target Encoding (Naive vs OOF vs M-OOF vs MB-OOF) | N/A | V1: 0.7545, V2: 0.6871, V3: 0.6981, V4: 0.6938 (Mean AUC) | N/A | SUCCESS | `experiments/artifacts/EXP_001/oof_predictions.pkl` | KEEP |
