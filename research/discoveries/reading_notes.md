# Reading Notes: Agentic Research Workflows in Top Kaggle Competitions

This document records concrete engineering practices performed by top Kaggle participants (author: Chris Deotte) across multiple 2026 Playground competitions and the KGMON Playbook. Every practice describes exclusively what the author and his agents did, supported by verbatim quotes of under 25 words with exact source locations. No subjective recommendations or ungrounded assertions are included.

---

## 1. Playground Series S6E11 (Topic 756276: "Sharing Code for 500 Models!")

### Practice 1.1: Human-Guided Autonomous Agent Code Generation
- **Status**: [QUOTED]
- **Location**: research/sources/s6e11_756276.md
- **Quote**: "All of these solutions' code was written by agents with me guiding them."
- **Concrete Details**: The author did not write manual competition code for the 2026 Playground series; instead, autonomous LLM agents wrote the code under human architectural guidance and house rules.

### Practice 1.2: Model Corpus Training for Agentic Tabular Competitions
- **Status**: [PARAPHRASED]
- **Location**: research/sources/s6e11_756276.md
- **Concrete Details**: The author open-sourced a public library of 500 models spanning six previous competitions (S6E3 through S6E10) to serve as a reference training corpus for future competitive agent workflows.

---

## 2. Playground Series S6E9 (Topic 745013: "1st Place - The AI Relay!")

### Practice 2.1: Multi-Generation Codebase Relay
- **Status**: [QUOTED]
- **Location**: research/sources/s6e9_745013.md
- **Quote**: "We passed one codebase between three generations of AI agents, like the baton in a relay race:"
- **Concrete Details**: The workflow staged three sequential agent generations across the month: Leg 1 (Codex GPT-5.6 Sol + Claude Code Fable 5), Leg 2 (Codex GPT-6-Astra + Fable 5.1), and Leg 3 (Claude Code Opus 5.5). Each generation inherited and built directly upon the exact repository left by the previous generation.

### Practice 2.2: Working Memory Preserved in Markdown Notes
- **Status**: [QUOTED]
- **Location**: research/sources/s6e9_745013.md
- **Quote**: "The baton was our code and our notes."
- **Concrete Details**: To counteract context loss between stateless agent sessions, the team maintained structured markdown artifacts: `plan.md` (forward agenda), `progress.md` (metrics and CV scores), `discoveries.md` (verified findings), and a closed ideas list (explicit negative constraints to prevent duplicated dead-ends).

### Practice 2.3: Parallel Subagent Literature and History Digest
- **Status**: [QUOTED]
- **Location**: research/sources/s6e9_745013.md
- **Quote**: "On its first day, Opus 5.5 sent out 13 helper agents. Each helper read one part of our history and wrote a report:"
- **Concrete Details**: When onboarding the final agent into a repository with ~1.8 million lines of code and 1,300 note files, 13 helper subagents read specific past competition folders, cookbooks, and notes, followed by 6 subagents auditing the codebase, enabling comprehensive onboarding within a single day.

### Practice 2.4: Inverse Metric Verification for Hidden Leaderboard Testing
- **Status**: [QUOTED]
- **Location**: research/sources/s6e9_745013.md
- **Quote**: "Replace every prediction p with 1 - p, and the line of people is turned around, so AUC becomes 1 - AUC."
- **Concrete Details**: To verify private models on the public test set without revealing true leaderboard progress to competitors, the team submitted inverted probability scores ($1 - p$), yielding an AUC of $1 - \text{AUC}$ (e.g. 0.053 for a 0.947 model) that did not displace their visible public rank until the final day.

---

## 3. Playground Series S6E8 (Topic 738592: "1st Place - Distributed Intelligence - NVIDIA Inference Hub")

### Practice 3.1: Autonomous Model Generation and Auto-Submission Loop
- **Status**: [QUOTED]
- **Location**: research/sources/s6e8_738592.md
- **Quote**: "Every time it added another 10-50 group of models, it would compute new ensemble CV score and submit to Kaggle LB by itself."
- **Concrete Details**: The author launched an autonomous Codex agent configured to download competition data, construct diverse models in batches of 10 to 50, compute updated cross-validation ensemble metrics, and submit predictions directly to Kaggle via the CLI without human intervention.

### Practice 3.2: Adversarial Head-to-Head Agent Competitions
- **Status**: [QUOTED]
- **Location**: research/sources/s6e8_738592.md
- **Quote**: "When one was lagging, we would share tips from the leading agent to the trailing agent"
- **Concrete Details**: Two disparate agent architectures (Codex GPT-5.6 Sol vs. Claude Code Fable 5) were set up in parallel competition on single-model benchmarks (Neural Networks vs. XGBoost). Cross-pollination of architectural tips from the leader to the follower pushed both agents to breakthrough single-model CV scores (0.97070 CV / 0.97174 LB).

### Practice 3.3: Offline Batch Reasoning Packets
- **Status**: [QUOTED]
- **Location**: research/sources/s6e8_738592.md
- **Quote**: "we asked Fable to build a tar.gz packet and write a prompt that we (humans) can (manually) upload to ChatGPT Pro"
- **Concrete Details**: The working manager agent compiled dataset summaries and open research questions into packaged tar.gz archives and prompts. These were processed in parallel by frontier reasoning models for multi-hour deep analysis, and the resulting discovery archives were fed back to the primary coding agents.

### Practice 3.4: Multi-Model Inference Hub Delegation
- **Status**: [QUOTED]
- **Location**: research/sources/s6e8_738592.md
- **Quote**: "Fable 5 assessed the skills of"
- **Concrete Details**: An agent evaluated the technical capabilities of external models accessible via NVIDIA Inference Hub (including Nemotron 3 Ultra, DeepSeek V4 Pro, Kimi K3, Gemini 3.7 Flash, Opus 5, and Qwen 3.8 27B) and assigned targeted sub-tasks to improve ensemble diversity.

---

## 4. Playground Series S6E5 (Topic 703615: "2nd Place - Autonomous Codex Yolo!")

### Practice 4.1: Persistent Local Leaderboard Tracking
- **Status**: [QUOTED]
- **Location**: research/sources/s6e5_703615.md
- **Quote**: "I asked Codex to maintain a local_leaderboard.md file with the top 10 CV score models."
- **Concrete Details**: The agent was required to maintain a persistent Markdown registry (`local_leaderboard.md`) cataloging the top 10 models evaluated strictly by local out-of-fold cross-validation scores.

### Practice 4.2: Unattended Multi-GPU Parallel Exploration
- **Status**: [QUOTED]
- **Location**: research/sources/s6e5_703615.md
- **Quote**: "I let Codex to use 4x A100 GPUs and keep running experiments in parallel and keep working and improving CV score"
- **Concrete Details**: The agent was given access to a 4x A100 GPU cluster with instructions to run parallel iterative feature engineering and hyperparameter tuning campaigns autonomously across multiple hours.

### Practice 4.3: Closed-Loop Autonomous Experimentation
- **Status**: [QUOTED]
- **Location**: research/sources/s6e5_703615.md
- **Quote**: "Codex wrote experiments, Codex ran the code on GPU, Codex logged the results (in local leaderboard), Codex analyzed the results,"
- **Concrete Details**: The agent autonomously executed every stage of empirical machine learning: code generation, GPU execution, metric logging, output analysis, and subsequent hypothesis formulation based on prior outcomes.

---

## 5. Playground Series S6E3 (Topic 686686: "1st Place - GPT5.4, Gemini3.1, ClaudeOpus4.6 - KGMON Playbook!")

### Practice 5.1: GPU Acceleration of Agent-Authored Code
- **Status**: [QUOTED]
- **Location**: research/sources/s6e3_686686.md
- **Quote**: "All of this solution's code was written by GPT5.4, Gemini3.1, ClaudeOpus4.6 and experimentation was accelerated with GPU, Nvidia cuDF, and Nvidia cuML."
- **Concrete Details**: Code generated by frontier models was coupled with GPU-accelerated libraries (cuDF for data manipulation, cuML for nearest neighbors, target encoding, and logistic regression stacking) to eliminate bottlenecks in high-throughput exploration.

### Practice 5.2: Scaled Model Factories Under Agent Execution
- **Status**: [QUOTED]
- **Location**: research/sources/s6e3_686686.md
- **Quote**: "They built and trained 850 models on 4xA100 GPU and wrote and ran 50 EDA scripts!"
- **Concrete Details**: Multi-agent authoring generated 600,000 lines of code across one month, producing 850 candidate models and 50 EDA scripts from which a final 150-model multi-level stack was constructed.

### Practice 5.3: Prompted Autonomous Exploratory Data Analysis
- **Status**: [QUOTED]
- **Location**: research/sources/s6e3_686686.md
- **Quote**: "In addition to building models, GPT5.4, Gemini3.1, ClaudeOpus4.6 were prompted to perform their own EDA"
- **Concrete Details**: Rather than receiving human-engineered features, the agents were instructed to discover discrepancies between synthetic competition data and original source distributions to design domain-specific signals (such as snap features, digit decomposition, and nested leak-free target encodings).

---

## 6. GitHub Repository: KGMON-Playbook-2026 (`cdeotte/KGMON-Playbook-2026`)

### Practice 6.1: Modular Playbook Pipeline Architecture
- **Status**: [QUOTED]
- **Location**: research/sources/kgmon_playbook.md
- **Quote**: "01_EDA.ipynb"
- **Concrete Details**: The repository structures competitive tabular modeling into disciplined sequential notebooks: `01_EDA.ipynb`, `02_Feature_Engineering.ipynb`, `03_Build_Baselines.ipynb`, `04_Stacking.ipynb`, `05_Hill_Climbing.ipynb`, `06_Pseudo_Label.ipynb`, and `07_Conclusion.ipynb`.

### Practice 6.2: Centralized Documentation and Hands-On Lab Infrastructure
- **Status**: [QUOTED]
- **Location**: research/sources/kgmon_playbook.md
- **Quote**: "* GTC Training Lab [here][3]"
- **Concrete Details**: The repository README provides canonical references linking modeling principles to technical blog documentation, presentation slides, and formal NVIDIA GTC training lab environments.
