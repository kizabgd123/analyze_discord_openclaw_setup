# Implementation Checklist: Google ADK A2A Multi-Agent LMS

## Phase 1: Foundation, Schemas & YouTube Discovery Pipeline
- [ ] 1.1 Create directory scaffold `a2a_lms/` and shared Pydantic data schemas in `a2a_lms/shared/schemas.py`
  - Verification: `python3 -c "import a2a_lms.shared.schemas as s; print('Schemas OK')"`
- [ ] 1.2 Implement YouTube discovery pipeline with entity extraction, query relaxation hierarchy, and live oEmbed validation in `a2a_lms/shared/youtube_lookup.py`
  - Verification: Test extraction and oEmbed verification against live YouTube endpoint with real video IDs
- [ ] 1.3 Write and execute unit verification suite for schemas and YouTube discovery in `a2a_lms/tests/test_youtube_lookup.py`
  - Verification: `python3 a2a_lms/tests/test_youtube_lookup.py` passes with exit code 0

## Phase 2: Agent-to-Agent Core (A2A Multi-Agent Engine)
- [ ] 2.1 Implement Principal Researcher Agent with NotebookLM source query and search grounding in `a2a_lms/agents/researcher/agent.py`
  - Verification: Execute sample research query and verify structured Serbian findings output
- [ ] 2.2 Implement Senior Judge Agent with strict Pydantic `JudgeFeedback` rubric (accuracy, Serbian language parity, domain fit) in `a2a_lms/agents/judge/agent.py`
  - Verification: Verify judge evaluates sample content and returns valid typed feedback
- [ ] 2.3 Implement LoopAgent & EscalationChecker orchestrating the consensus loop in `a2a_lms/agents/orchestrator/agent.py`
  - Verification: Test loop execution up to 3 iterations with automated escalation on pass
- [ ] 2.4 Implement Lead Content Builder Agent producing 7 masterclass modules in `a2a_lms/agents/content_builder/agent.py`
  - Verification: Test generation of full 7-part curriculum with embedded `[mm:ss]` timestamps

## Phase 3: Interactive LMS Web Application & Frontend Modules
- [ ] 3.1 Create modern Dark/Light responsive LMS stylesheet in `a2a_lms/app/frontend/style.css`
  - Verification: Validate CSS syntax and responsive breakpoints for 3D flashcards and video player
- [ ] 3.2 Build interactive LMS client engine in `a2a_lms/app/frontend/course.js`
  - Verification: Validate HTML5 postMessage video seeking, active recall 3D flip, quiz scoring, and certificate generator
- [ ] 3.3 Create LMS presentation views in `a2a_lms/app/frontend/index.html` and `a2a_lms/app/frontend/course.html`
  - Verification: Verify DOM elements match IDs and classes expected by `course.js` and Science sidecar link handlers

## Phase 4: FastAPI Service, SSE Streaming & Live Verification
- [ ] 4.1 Implement FastAPI application with real-time SSE stream endpoint `/api/chat_stream` and course delivery in `a2a_lms/app/main.py`
  - Verification: `python3 -c "import a2a_lms.app.main; print('FastAPI App Loaded OK')"`
- [ ] 4.2 Write and execute end-to-end integration test validating full A2A pipeline without mocks in `a2a_lms/tests/test_a2a_pipeline.py`
  - Verification: `python3 a2a_lms/tests/test_a2a_pipeline.py` passes all zero-mock assertions with exit code 0
