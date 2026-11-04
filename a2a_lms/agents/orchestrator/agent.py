"""LMS Multi-Agent Orchestrator (Google ADK 2.0 A2A Architecture).
Coordinates Researcher, Judge, YouTube Discovery and Content Builder agents.
"""

import logging
from typing import Optional, Callable, Dict, Any
from a2a_lms.shared.schemas import CoursePayload, ResearchFindings, JudgeFeedback, YouTubeMetadata
from a2a_lms.shared.youtube_lookup import find_embeddable_youtube_video
from a2a_lms.agents.researcher.agent import PrincipalResearcherAgent
from a2a_lms.agents.judge.agent import SeniorJudgeAgent
from a2a_lms.agents.content_builder.agent import LeadContentBuilderAgent

logger = logging.getLogger("a2a_lms.orchestrator")


class LMSOrchestrator:
    """Master orchestrator executing the A2A consensus loop and course pipeline."""

    def __init__(self, notebook_id: str = "9c8878e1-1fb4-4035-b022-7678a10be7f3"):
        self.notebook_id = notebook_id
        self.researcher = PrincipalResearcherAgent(notebook_id=notebook_id)
        self.judge = SeniorJudgeAgent()
        self.content_builder = LeadContentBuilderAgent()

    async def run(
        self,
        topic: str,
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> CoursePayload:
        logger.info(f"LMSOrchestrator starting A2A generation pipeline for: '{topic}'")

        def emit(msg: str):
            logger.info(f"[A2A Orchestrator] {msg}")
            if on_progress:
                try:
                    on_progress(msg)
                except Exception as e:
                    logger.warning(f"Error in progress callback: {e}")

        # 1. YouTube discovery and live verification
        emit("📺 Verifikacija autentičnog YouTube tutorijala i oEmbed poglavlja...")
        # Determine rough domain for fallback resolution
        lower_t = topic.lower()
        domain = "science" if any(w in lower_t for w in ["biolog", "protein", "molekul"]) \
            else "sports" if any(w in lower_t for w in ["tenis", "sport", "fudbal"]) \
            else "default"
        youtube_meta: YouTubeMetadata = find_embeddable_youtube_video(topic, domain_type=domain)

        # 2. Researcher & Judge Consensus Loop (LoopAgent + EscalationChecker)
        emit("🔍 Principal Researcher analizira temu i konsultuje NotebookLM znanje...")
        revision_notes: Optional[str] = None
        findings: Optional[ResearchFindings] = None
        judge_feedback: Optional[JudgeFeedback] = None
        max_iterations = 3

        for iteration in range(1, max_iterations + 1):
            findings = await self.researcher.research(topic, revision_notes=revision_notes)
            
            emit(f"⚖️ Senior Judge vrši reviziju istraživanja (Iteracija {iteration}/{max_iterations})...")
            judge_feedback = self.judge.evaluate(findings)

            if judge_feedback.pass_status:
                emit(f"✅ Senior Judge odobrio kurikulum (Ocena: {judge_feedback.overall_score}/10).")
                break
            else:
                emit(f"⚠️ Potrebna dorada: {judge_feedback.critique}")
                missing_str = ", ".join(judge_feedback.missing_aspects) if judge_feedback.missing_aspects else judge_feedback.critique
                revision_notes = f"Iteracija {iteration} primedbe: {missing_str}"

        # 3. Content Builder Synthesis
        emit("✍️ Lead Content Builder kreira 7 celina masterclass kursa i interaktivne module...")
        course_payload = self.content_builder.build_course(
            findings=findings,
            judge_feedback=judge_feedback,
            youtube_meta=youtube_meta,
        )

        emit(f"🎉 Masterclass kurs '{topic}' je uspešno kreiran i verifikovan (Hash: {course_payload.verification_hash})!")
        return course_payload
