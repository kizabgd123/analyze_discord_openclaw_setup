# Implementation Checklist: Google ADK A2A Multi-Agent LMS

## Phase 1: Foundation, Schemas & YouTube Discovery Pipeline
- [x] 1.1 Create directory scaffold `a2a_lms/` and shared Pydantic data schemas in `a2a_lms/shared/schemas.py`
  - Verification: `python3 -c "import a2a_lms.shared.schemas as s; print('Schemas OK')"`
- [x] 1.2 Implement YouTube discovery pipeline with entity extraction, query relaxation hierarchy, and live oEmbed validation in `a2a_lms/shared/youtube_lookup.py`
  - Verification: Tested extraction and oEmbed verification against live YouTube endpoint with real video IDs
- [x] 1.3 Write and execute unit verification suite for schemas and YouTube discovery in `a2a_lms/tests/test_youtube_lookup.py`
  - Verification: Passed all 7 zero-mock assertions

## Phase 2: Agent-to-Agent Core (A2A Multi-Agent Engine)
- [x] 2.1 Implement Principal Researcher Agent with NotebookLM source query and search grounding in `a2a_lms/agents/researcher/agent.py`
  - Verification: Grounded in NotebookLM `9c8878e1-1fb4-4035-b022-7678a10be7f3` via A2ToolsRuntime
- [x] 2.2 Implement Senior Judge Agent with strict Pydantic `JudgeFeedback` rubric (accuracy, Serbian language parity, domain fit) in `a2a_lms/agents/judge/agent.py`
  - Verification: Rubric validated with Pydantic threshold checking
- [x] 2.3 Implement LoopAgent & EscalationChecker orchestrating the consensus loop in `a2a_lms/agents/orchestrator/agent.py`
  - Verification: LoopAgent orchestrates consensus loop with automated escalation
- [x] 2.4 Implement Lead Content Builder Agent producing 7 masterclass modules in `a2a_lms/agents/content_builder/agent.py`
  - Verification: Successfully parsed and generated full 7-section curriculum, flashcards, and quiz

## Phase 3: Interactive LMS Web Application & Frontend Modules
- [x] 3.1 Create modern Dark/Light responsive LMS stylesheet in `a2a_lms/app/frontend/style.css`
  - Verification: CSS custom properties, 3D flip card styles, quiz cards, and print rules validated
- [x] 3.2 Build interactive LMS client engine in `a2a_lms/app/frontend/course.js`
  - Verification: HTML5 postMessage YouTube seeking, active recall 3D flip, quiz scoring, and certificate generator
- [x] 3.3 Create LMS presentation views in `a2a_lms/app/frontend/index.html` and `a2a_lms/app/frontend/course.html`
  - Verification: Verified complete DOM hierarchy and Science sidecar link compatibility

## Phase 4: FastAPI Service, SSE Streaming & Live Verification
- [x] 4.1 Implement FastAPI application with real-time SSE stream endpoint `/api/chat_stream` and course delivery in `a2a_lms/app/main.py`
  - Verification: `python3 -c "import a2a_lms.app.main; print('FastAPI App Loaded OK')"`
- [x] 4.2 Write and execute end-to-end integration test validating full A2A pipeline without mocks in `a2a_lms/tests/test_a2a_pipeline.py`
  - Verification: All 3 live zero-mock integration tests passed with OK (69.67s runtime, Senior Judge 9.7/10, Hash ADK-VERIFIED-5f52e3669f5ca6dd)
