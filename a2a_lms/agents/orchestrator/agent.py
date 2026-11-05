"""LMS Multi-Agent Orchestrator (Google ADK 2.0 A2A Architecture).
Coordinates Researcher, Judge, YouTube Discovery and Content Builder agents.
Implements durable execution checkpointing, ReAct trace recording, cost budgeting,
and anti-fabrication grounding checks per the autonomous-agents skill.
"""

import logging
import asyncio
from typing import Optional, Callable, Dict, Any
from a2a_lms.shared.schemas import CoursePayload, ResearchFindings, JudgeFeedback, YouTubeMetadata, ExecutionMetrics
from a2a_lms.shared.youtube_lookup import find_embeddable_youtube_video
from a2a_lms.shared.cost_guard import CostAndStepGuard, StepLimitExceededError, CostLimitExceededError
from a2a_lms.shared.checkpoint import LMSCheckpointManager
from a2a_lms.agents.researcher.agent import PrincipalResearcherAgent
from a2a_lms.agents.judge.agent import SeniorJudgeAgent
from a2a_lms.agents.content_builder.agent import LeadContentBuilderAgent

logger = logging.getLogger("a2a_lms.orchestrator")


class LMSOrchestrator:
    """Master orchestrator executing the durable A2A consensus loop and course pipeline."""

    def __init__(self, notebook_id: Optional[str] = None):
        self.notebook_id = notebook_id
        self.researcher = PrincipalResearcherAgent(notebook_id=notebook_id)
        self.judge = SeniorJudgeAgent()
        self.content_builder = LeadContentBuilderAgent()
        self.checkpoint_manager = LMSCheckpointManager()

    async def run(
        self,
        topic: str,
        thread_id: Optional[str] = None,
        resume_from_checkpoint: bool = False,
        on_progress: Optional[Callable[[str], None]] = None,
        max_steps: int = 15,
        max_cost_usd: float = 0.50,
    ) -> CoursePayload:
        """Executes full autonomous multi-agent pipeline with checkpoints and cost control."""
        cost_guard = CostAndStepGuard(max_steps=max_steps, max_cost_usd=max_cost_usd)
        active_thread_id = thread_id or self.checkpoint_manager.create_thread_id("course")
        cost_guard.checkpoint_id = active_thread_id

        logger.info(
            f"LMSOrchestrator starting autonomous pipeline for: '{topic}' | "
            f"Thread: {active_thread_id} | Resume: {resume_from_checkpoint}"
        )

        def emit(msg: str):
            logger.info(f"[A2A Orchestrator] {msg}")
            if on_progress:
                try:
                    on_progress(msg)
                except Exception as e:
                    logger.warning(f"Error in progress callback: {e}")

        youtube_meta: Optional[YouTubeMetadata] = None
        findings: Optional[ResearchFindings] = None
        judge_feedback: Optional[JudgeFeedback] = None
        starting_iteration = 1

        # Check if resuming from an existing checkpoint
        if resume_from_checkpoint and thread_id:
            saved_state = self.checkpoint_manager.load_checkpoint(thread_id)
            if saved_state and "state" in saved_state:
                st = saved_state["state"]
                current_stage = saved_state.get("current_stage", "")
                emit(f"🔄 Nastavljam izvršenje sa checkpoint-a: {current_stage} (Thread: {thread_id})...")
                cost_guard.resumed_from_checkpoint = True

                if "youtube_metadata" in st:
                    youtube_meta = YouTubeMetadata(**st["youtube_metadata"])
                if "research_findings" in st:
                    findings = ResearchFindings(**st["research_findings"])
                if "judge_feedback" in st:
                    judge_feedback = JudgeFeedback(**st["judge_feedback"])
                starting_iteration = saved_state.get("iteration", 1)

        try:
            # 1. YouTube discovery and live verification
            if not youtube_meta:
                cost_guard.before_step("LMSOrchestrator", "discover_verified_youtube_video")
                emit("📺 Verifikacija autentičnog YouTube tutorijala i oEmbed poglavlja...")
                
                lower_t = topic.lower()
                domain = "science" if any(w in lower_t for w in ["biolog", "protein", "molekul"]) \
                    else "sports" if any(w in lower_t for w in ["tenis", "sport", "fudbal"]) \
                    else "default"
                
                youtube_meta = find_embeddable_youtube_video(topic, domain_type=domain)
                
                cost_guard.record_step(
                    agent_name="LMSOrchestrator",
                    thought=f"Za temu '{topic}' (domen: {domain}) vršim pretragu autentičnog video tutorijala sa vremenskim oznakama i validnim oEmbed odzivom.",
                    action=f"find_embeddable_youtube_video(topic='{topic}', domain='{domain}')",
                    observation=f"Pronađen verifikovan video: '{youtube_meta.title}' (ID: {youtube_meta.video_id}) sa {len(youtube_meta.chapters)} poglavlja.",
                    reflection=f"oEmbed verifikacija uspešna={youtube_meta.verified}.",
                )

                self.checkpoint_manager.save_checkpoint(
                    thread_id=active_thread_id,
                    stage="YOUTUBE_DISCOVERED",
                    topic=topic,
                    state_data={"youtube_metadata": youtube_meta.model_dump()},
                )

            # 2. Researcher & Judge Consensus Loop (Evaluator-Optimizer reflection pattern)
            if not judge_feedback or not judge_feedback.pass_status:
                emit("🔍 Principal Researcher vrši rigoroznu domensku analizu i priprema kurikulum...")
                revision_notes: Optional[str] = None
                max_consensus_iterations = 3

                for iteration in range(starting_iteration, max_consensus_iterations + 1):
                    cost_guard.before_step("PrincipalResearcherAgent", f"research_iteration_{iteration}")
                    findings = await self.researcher.research(
                        topic=topic,
                        revision_notes=revision_notes,
                        cost_guard=cost_guard,
                    )

                    cost_guard.before_step("SeniorJudgeAgent", f"evaluate_iteration_{iteration}")
                    emit(f"⚖️ Senior Judge vrši reviziju istraživanja (Iteracija {iteration}/{max_consensus_iterations})...")
                    judge_feedback = self.judge.evaluate(findings, cost_guard=cost_guard)

                    # Save checkpoint of research iteration
                    self.checkpoint_manager.save_checkpoint(
                        thread_id=active_thread_id,
                        stage=f"RESEARCH_ITERATION_{iteration}",
                        topic=topic,
                        iteration=iteration,
                        state_data={
                            "youtube_metadata": youtube_meta.model_dump(),
                            "research_findings": findings.model_dump(),
                            "judge_feedback": judge_feedback.model_dump(),
                        },
                    )

                    if judge_feedback.pass_status:
                        emit(f"✅ Senior Judge odobrio kurikulum (Ocena: {judge_feedback.overall_score}/10 | Utemeljenost potvrdjena).")
                        self.checkpoint_manager.save_checkpoint(
                            thread_id=active_thread_id,
                            stage="RESEARCH_APPROVED",
                            topic=topic,
                            iteration=iteration,
                            state_data={
                                "youtube_metadata": youtube_meta.model_dump(),
                                "research_findings": findings.model_dump(),
                                "judge_feedback": judge_feedback.model_dump(),
                            },
                        )
                        break
                    else:
                        emit(f"⚠️ Potrebna dorada kurikuluma: {judge_feedback.critique}")
                        missing_str = ", ".join(judge_feedback.missing_aspects) if judge_feedback.missing_aspects else judge_feedback.critique
                        revision_notes = f"Iteracija {iteration} primedbe sudije: {missing_str}"

            # 3. Content Builder Synthesis
            cost_guard.before_step("LeadContentBuilderAgent", "synthesize_curriculum")
            emit("✍️ Lead Content Builder kreira 7 celina masterclass kursa i interaktivne module...")
            
            course_payload = self.content_builder.build_course(
                findings=findings,
                judge_feedback=judge_feedback,
                youtube_meta=youtube_meta,
                cost_guard=cost_guard,
            )

            # Checkpoint final completion
            self.checkpoint_manager.save_checkpoint(
                thread_id=active_thread_id,
                stage="COMPLETED",
                topic=topic,
                state_data={"course_payload": course_payload.model_dump()},
            )

            emit(f"🎉 Masterclass kurs '{topic}' je uspešno kreiran i verifikovan (Hash: {course_payload.verification_hash})!")
            return course_payload

        except (StepLimitExceededError, CostLimitExceededError) as guard_err:
            logger.error(f"[CostGuard Failure] {guard_err}")
            emit(f"🛑 Sigurnosna blokada: {guard_err}")
            raise
        except Exception as unhandled_err:
            logger.error(f"[Orchestrator Unhandled Error] {unhandled_err}", exc_info=True)
            # Rollback / save failure checkpoint for post-mortem
            self.checkpoint_manager.save_checkpoint(
                thread_id=active_thread_id,
                stage="FAILED",
                topic=topic,
                state_data={"error": str(unhandled_err)},
            )
            raise
