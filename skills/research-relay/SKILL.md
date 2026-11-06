---
name: research-relay
description: Reciprocal non-adversarial knowledge relay protocol. Receives a peer agent's completed discoveries report and produces a structured extension report (relay_<agent_id>.md) with new discoveries, sources, hypotheses, and experiment proposals without debate.
---

# Reciprocal Research Relay Protocol

## Mission
Execute a constructive, non-adversarial, reciprocal knowledge relay between independent researchers. Each researcher reads the other's completed discovery findings and produces a dedicated relay extension report (`relay_<agent_id>.md`). Both agents advance the research with new literature, additional empirical facts, refined hypotheses, and concrete experiment specifications. Strictly eliminate argumentative debates, philosophical disputes, or adversarial discourse.

## Guiding Principles

1. **Reciprocal Extension Over Debate:**
   - Bot-to-bot chat and argumentative debate waste tokens asserting intellectual dominance.
   - Reciprocal Relay treats each peer report as an empirical clue dataset.
   - Bilateral exchange: Agent A reads `discovery_B.md` to output `relay_A.md`; Agent B reads `discovery_A.md` to output `relay_B.md`.

2. **Protocol Execution:**
   - **Step 1:** Ingest peer discovery artifact from `research/discoveries/discovery_<peer_id>.md`.
   - **Step 2:** Cross-source and expand literature in `research/sources.md`.
   - **Step 3:** Synthesize and formalize hypotheses into falsifiable candidates.
   - **Step 4:** Parameterize concrete experiment configurations (data splits, model families, feature sets).
   - **Step 5:** Save report to `research/discoveries/relay_<agent_id>.md`.

3. **Report Contract (`relay_<agent_id>.md`):**
   - 1. Peer Clues & Findings Leveraged
   - 2. Complementary Discoveries & New Sources
   - 3. Synthesized & Ranked Hypotheses
   - 4. Concrete Experiment Proposals
   - 5. Handoff Checklist
