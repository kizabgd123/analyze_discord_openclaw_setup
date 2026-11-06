---
name: research-relay
description: Reciprocal non-adversarial knowledge relay protocol. Receives a peer agent's completed discoveries report and produces a structured extension report (relay_A.md / relay_B.md) with new discoveries, sources, hypotheses, and experiment proposals without debate.
---

# Reciprocal Research Relay Protocol

## Mission

Execute a constructive, non-adversarial, **reciprocal** knowledge relay across independent agents. In a reciprocal relay, each researcher reads the other's completed discovery findings and produces a dedicated relay extension report (`relay_kiza.md` / `relay_kreten.md`). Both agents advance the research with new literature, additional empirical facts, refined hypotheses, and concrete experiment specifications. Strictly eliminate argumentative debates, philosophical disputes, or adversarial discourse.

## Guiding Principles

1. **Reciprocal Knowledge Extension over Debate:**
   - Traditional bot-to-bot chat or adversarial debate wastes tokens arguing over superiority.
   - Reciprocal Research Relay treats each peer report as a high-value dataset of clues, negative results, and initial hypotheses.
   - The relay is bilateral:
     - Agent A reads Agent B's discoveries and outputs `research/discoveries/relay_A.md`.
     - Agent B reads Agent A's discoveries and outputs `research/discoveries/relay_B.md`.
   - Your mandate is to *advance* the baton: "Given what my peer discovered, what new literature exists? What missing variables or failure modes did they overlook? How can their findings be translated into an empirical experiment?"

2. **Reciprocal Relay Protocol Execution:**
   - **Step 1: Ingest Peer Discovery Artifact:** Read the peer's completed `discoveries.md` thoroughly.
   - **Step 2: Cross-Source & Literature Expansion:** Identify cited sources, search for complementary literature, and add new verified references to `research/sources.md`.
   - **Step 3: Advance & Formalize Hypotheses:** Combine the peer's insights with your own independent domain knowledge to formulate formal, falsifiable hypotheses.
   - **Step 4: Parameterize Experiment Candidates:** Translate hypotheses into concrete, executable experiment designs (algorithm, baseline metric, intervention, dataset/fold split, parameter grid).
   - **Step 5: Output Dedicated Relay Extension:** Save to `research/discoveries/relay_<agent_id>.md`.

3. **Standard Reciprocal Relay Report Contract (`relay_<agent_id>.md`):**
   - **1. Peer Clues & Findings Leveraged:** Specific discoveries and facts from the peer report that serve as starting points.
   - **2. Complementary Discoveries & New Sources:** Additional evidence, mathematical derivations, or empirical facts discovered during relay extension.
   - **3. Synthesized & Ranked Hypotheses:** Upgraded hypotheses with precise falsification bounds and expected information gain.
   - **4. Concrete Experiment Proposals:** Priority-ranked experiment configurations ready for immediate execution by the Experiment Engineer.
   - **5. Handoff Checklist:** Script requirements, validation fold constraints, evaluation metrics, and resource ceilings.
