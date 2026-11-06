---
name: research-discovery
description: Independent research and discovery skill. Conducts unanchored, isolated literature review, exploratory data analysis, and mechanistic hypothesis formation without peer bias.
---

# Independent Research Discovery Skill

## Purpose
Execute rigorous, independent exploration of scientific, algorithmic, or ML domains. Agents using this skill must operate in contextual isolation from peer researchers to avoid premature groupthink, anchoring bias, and collective blind spots.

## Protocol Instructions

1. **Inherit Objective & Known Boundaries:**
   - Read `objective.md` to identify constraints and target goals.
   - Read `findings/negative_findings.md` to avoid previously verified dead ends.
   - Do NOT inspect peer researchers' current in-progress discovery drafts.

2. **Literature & Methodological Exploration:**
   - Search literature, arXiv papers, Kaggle winner write-ups, or codebases for relevant mechanisms.
   - Record all verified citations and links in `research/sources.md`.

3. **Mechanistic Hypotheses Formulation:**
   - Propose 2-4 formal, mechanistic explanations for potential improvements.
   - Identify potential failure modes, data leakage risks, and edge cases.

4. **Output Contract:**
   - Write output to `research/discoveries/discovery_<agent_id>.md`.
   - Must contain:
     1. Domain Background & Literature Ingested
     2. Proposed Mechanistic Insights
     3. Initial Hypotheses (Statement, Rationale, Test Idea)
     4. Identified Risk Factors & Edge Cases
     5. Open Questions for the Relay Phase
