---
name: research-relay
description: Non-adversarial knowledge relay protocol. Receives a peer agent's completed discoveries report and extends, deepens, or synthesizes it into actionable experiments without debate.
---

# Research Relay Protocol

## Mission

Execute a constructive, non-adversarial knowledge relay across independent agents. When given another researcher's completed `discoveries.md`, read and extend their findings, build upon their verified evidence, synthesize complementary insights, and formulate concrete experiments. Strictly avoid argumentative debates, philosophical disputes, or conversational back-and-forth.

## Guiding Principles

1. **Extension over Debate:**
   - Traditional bot-to-bot chat wastes tokens arguing over prestige or rhetorical superiority.
   - Research Relay treats the peer's report as a valuable dataset of clues, negative results, and initial hypotheses.
   - Your job is to *advance* the baton: "Given what Researcher A discovered, what new doors does this open? How can their partial finding be translated into an empirical test?"

2. **Protocol Steps:**
   - **Step 1: Read Peer Report:** Thoroughly inspect the peer's `discoveries.md` artifact.
   - **Step 2: Cross-Check Evidence:** Check whether the peer's facts align with your independent domain knowledge or if there are critical missing variables.
   - **Step 3: Advance Hypotheses:** Combine the peer's discoveries with your own insights to produce higher-order hypotheses.
   - **Step 4: Formalize Experiment Proposals:** Convert abstract ideas into parameterized experiment configurations (algorithm, baseline, candidate modification, evaluation metric, resource limit).
   - **Step 5: Output Relay Extension:** Save to `research/discoveries/<researcher_id>_relay_extension.md`.

3. **Standard Relay Extension Format:**
   - **Peer Clues Utilized:** Which discoveries from the peer report served as the launching point.
   - **Synthesized Insights:** New patterns emerging from merging both lines of investigation.
   - **Refined / Disproved Hypotheses:** Upgraded hypotheses with tighter bounds or falsification conditions.
   - **Concrete Experiment Candidates:** Priority-ranked experiments ready for the Experiment Engineer.
   - **Handoff Checklist:** Required inputs, scripts, and validation criteria for execution.
