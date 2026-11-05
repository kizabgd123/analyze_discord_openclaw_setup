"""Zero-Mock Unit Tests for Autonomous Agent Guards and Durable Checkpoints.
Verifies Step Limits, Cost Budgeting, ReAct Traces, and Checkpoint Resumption
per the autonomous-agents skill specification.
"""

import unittest
import asyncio
import tempfile
import shutil
from pathlib import Path

from a2a_lms.shared.schemas import (
    ResearchFindings,
    JudgeFeedback,
    YouTubeMetadata,
    Chapter,
    CoursePayload,
)
from a2a_lms.shared.cost_guard import (
    CostAndStepGuard,
    StepLimitExceededError,
    CostLimitExceededError,
)
from a2a_lms.shared.checkpoint import LMSCheckpointManager
from a2a_lms.agents.orchestrator.agent import LMSOrchestrator
from a2a_lms.agents.judge.agent import SeniorJudgeAgent


class TestAutonomousGuardsAndCheckpoints(unittest.TestCase):
    """Rigorous tests verifying autonomous-agents guardrails and durability."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.checkpoint_mgr = LMSCheckpointManager(checkpoint_dir=self.temp_dir)

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_step_limit_enforcement(self):
        """Guard must halt execution when max_steps is exceeded to prevent infinite loops."""
        guard = CostAndStepGuard(max_steps=3, max_cost_usd=1.0)
        
        # Step 1, 2, 3 should succeed
        guard.before_step("AgentA", "step1")
        guard.before_step("AgentA", "step2")
        guard.before_step("AgentA", "step3")
        
        # Step 4 must raise StepLimitExceededError
        with self.assertRaises(StepLimitExceededError) as ctx:
            guard.before_step("AgentA", "step4")
        self.assertIn("exceeded maximum step limit", str(ctx.exception))

    def test_cost_limit_enforcement(self):
        """Guard must halt execution when cost limit is exceeded."""
        guard = CostAndStepGuard(max_steps=20, max_cost_usd=0.0001)
        
        guard.before_step("AgentB", "action1")
        # Record a step with massive text that exceeds the microscopic budget
        guard.record_step(
            agent_name="AgentB",
            thought="Thinking...",
            action="call_big_api",
            observation="Done",
            input_text="A" * 10000,
            output_text="B" * 10000,
        )
        
        # Next step should be blocked by cost budget
        with self.assertRaises(CostLimitExceededError) as ctx:
            guard.before_step("AgentB", "action2")
        self.assertIn("exceeded maximum budget", str(ctx.exception))

    def test_react_trace_recording(self):
        """ReAct trace steps must capture Thought, Action, Observation, Reflection."""
        guard = CostAndStepGuard(max_steps=10)
        guard.before_step("Researcher", "query")
        step = guard.record_step(
            agent_name="Researcher",
            thought="Potrebno je istražiti mentalne modele.",
            action="query_notebooklm()",
            observation="Dobijeno 500 reči znanja.",
            reflection="Znanje je relevantno i utemeljeno.",
            input_text="input prompt",
            output_text="output result",
        )
        
        self.assertEqual(len(guard.traces), 1)
        self.assertEqual(step.agent_name, "Researcher")
        self.assertEqual(step.step_number, 1)
        self.assertIn("mentalne modele", step.thought)
        self.assertIn("query_notebooklm", step.action)
        self.assertIn("500 reči", step.observation)
        self.assertIn("relevantno", step.reflection)
        self.assertGreater(step.tokens_used, 0)

        metrics = guard.get_metrics(grounding_confidence=0.98)
        self.assertEqual(metrics.total_steps, 1)
        self.assertGreater(metrics.total_estimated_tokens, 0)
        self.assertEqual(metrics.grounding_confidence, 0.98)

    def test_durable_checkpoint_save_and_load(self):
        """Checkpoints must save atomically to disk and load accurately."""
        thread_id = self.checkpoint_mgr.create_thread_id("test")
        
        test_meta = YouTubeMetadata(
            video_id="11111111111",
            title="Durable Execution in ADK",
            author="Google Cloud",
            duration_seconds=600,
            duration_formatted="10:00",
            chapters=[Chapter(timestamp="00:00", seconds=0, title="Intro")],
            embed_url="https://www.youtube-nocookie.com/embed/11111111111",
            verified=True,
        )

        saved_path = self.checkpoint_mgr.save_checkpoint(
            thread_id=thread_id,
            stage="YOUTUBE_DISCOVERED",
            topic="Durable Agents",
            state_data={"youtube_metadata": test_meta.model_dump()},
            iteration=1,
        )
        self.assertTrue(Path(saved_path).exists())

        # Load back
        loaded = self.checkpoint_mgr.load_checkpoint(thread_id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["thread_id"], thread_id)
        self.assertEqual(loaded["current_stage"], "YOUTUBE_DISCOVERED")
        self.assertEqual(loaded["state"]["youtube_metadata"]["video_id"], "11111111111")

        # List checkpoints
        all_ckpts = self.checkpoint_mgr.list_checkpoints()
        self.assertEqual(len(all_ckpts), 1)
        self.assertEqual(all_ckpts[0]["thread_id"], thread_id)

    def test_orchestrator_checkpoint_resumption(self):
        """Orchestrator must resume from a checkpoint without re-querying already verified stages."""
        thread_id = self.checkpoint_mgr.create_thread_id("resume-test")
        
        test_meta = YouTubeMetadata(
            video_id="22222222222",
            title="Pre-Verified Tutorial",
            author="Verified Channel",
            duration_seconds=720,
            duration_formatted="12:00",
            chapters=[
                Chapter(timestamp="00:00", seconds=0, title="Uvod"),
                Chapter(timestamp="03:00", seconds=180, title="Arhitektura"),
            ],
            embed_url="https://www.youtube-nocookie.com/embed/22222222222",
            verified=True,
        )

        test_findings = ResearchFindings(
            topic="Testna Tema za Resume",
            domain_type="technical",
            mental_models=["Model A", "Model B"],
            core_principles=["Princip 1", "Princip 2"],
            practical_steps=["Korak 1", "Korak 2", "Korak 3"],
            traps_and_pitfalls=["Greška 1", "Greška 2"],
            source_citations=["Izvorni citat iz baze znanja"],
            raw_markdown="Detaljno istraživanje teme.",
        )

        test_feedback = JudgeFeedback(
            accuracy_score=9,
            language_parity_score=10,
            completeness_score=9,
            overall_score=9.3,
            pass_status=True,
            grounding_verified=True,
            critique="Istraživanje u potpunosti odobreno.",
            missing_aspects=[],
        )

        # Save checkpoint as RESEARCH_APPROVED
        self.checkpoint_mgr.save_checkpoint(
            thread_id=thread_id,
            stage="RESEARCH_APPROVED",
            topic="Testna Tema za Resume",
            state_data={
                "youtube_metadata": test_meta.model_dump(),
                "research_findings": test_findings.model_dump(),
                "judge_feedback": test_feedback.model_dump(),
            },
            iteration=1,
        )

        # Run orchestrator with resume_from_checkpoint=True
        orchestrator = LMSOrchestrator()
        orchestrator.checkpoint_manager = self.checkpoint_mgr

        course = asyncio.run(
            orchestrator.run(
                topic="Testna Tema za Resume",
                thread_id=thread_id,
                resume_from_checkpoint=True,
            )
        )

        self.assertIsNotNone(course)
        self.assertEqual(course.youtube_metadata.video_id, "22222222222")
        self.assertTrue(course.execution_metrics.resumed_from_checkpoint)
        self.assertEqual(course.execution_metrics.checkpoint_id, thread_id)
        self.assertEqual(len(course.sections), 7)
        self.assertIn("ADK-VERIFIED-", course.verification_hash)


if __name__ == "__main__":
    unittest.main()
