# CONTINUITY.md — OpenClaw / Antigravity

- **Active Goal**: Build separate Google ADK A2A Multi-Agent LMS Course Architecture grounded in NotebookLM `9c8878e1-1fb4-4035-b022-7678a10be7f3` with zero-mock verification.
- **Current Phase**: planning
- **Working Context**:
  - Existing Discord bot and web application remain untouched in their respective directories.
  - Dedicated package `a2a_lms/` contains agents (orchestrator, researcher, judge, content builder), shared tools (YouTube discovery & oEmbed validator), and standalone LMS frontend.
  - 100% grounded in verified NotebookLM sources (Architecture 2026, YouTube Pipeline, Content Hand-off, Elimination of synthetic slides, 7 interactive modules, FastAPI blueprint).
  - Strict compliance with `judge_guard.py` and `MASTER_ORCHESTRATION.md`.
- **Next Actions**:
  - `1.1` Create directory scaffold `a2a_lms/` and shared Pydantic data schemas in `a2a_lms/shared/schemas.py`.
  - `1.2` Implement YouTube discovery pipeline with entity extraction, query relaxation hierarchy, and live oEmbed validation in `a2a_lms/shared/youtube_lookup.py`.
  - `1.3` Write and execute unit verification suite for schemas and YouTube discovery in `a2a_lms/tests/test_youtube_lookup.py`.
