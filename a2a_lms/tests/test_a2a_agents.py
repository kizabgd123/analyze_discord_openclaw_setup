"""Zero-Mock Verification Suite: Agent-to-Agent Logic & Rubric Constraints.
Tests authentic Senior Judge evaluations, Pydantic validation, and Content Builder parsing.
"""

import unittest
from a2a_lms.shared.schemas import ResearchFindings, JudgeFeedback, YouTubeMetadata, Chapter
from a2a_lms.agents.judge.agent import SeniorJudgeAgent
from a2a_lms.agents.content_builder.agent import LeadContentBuilderAgent


class TestA2AAgents(unittest.TestCase):
    """Verifies that agents strictly adhere to the NotebookLM rubric and contracts."""

    def setUp(self):
        self.sample_findings = ResearchFindings(
            topic="Google ADK A2A Multi-Agent Sistemi",
            domain_type="technical",
            mental_models=["Konsenzus agenata", "Deterministički čuvar stanja"],
            core_principles=["A2A protokol", "Zero-mock verifikacija", "Interaktivno učenje"],
            practical_steps=[
                "Kreiranje Pydantic šema",
                "Integracija YouTube discovery servisa",
                "Povezivanje NotebookLM sveske",
                "Izgradnja interaktivnog interfejsa",
            ],
            traps_and_pitfalls=["Korišćenje sintetičkih slajdova", "Lažiranje testova"],
            sidecar_type=None,
            raw_markdown="Detaljan pregled arhitekture Google ADK agenata.",
        )

        self.sample_youtube = YouTubeMetadata(
            video_id="u4ydH-QvPeg",
            title="OpenClaw Tutorial for Beginners - Crash Course",
            author="Adrian Twarog",
            duration_seconds=478,
            duration_formatted="07:58",
            chapters=[
                Chapter(timestamp="00:00", seconds=0, title="Uvod i okruženje"),
                Chapter(timestamp="02:30", seconds=150, title="Mentalni model"),
                Chapter(timestamp="05:15", seconds=315, title="A2A demonstracija"),
            ],
            embed_url="https://www.youtube-nocookie.com/embed/u4ydH-QvPeg",
            verified=True,
        )

    def test_judge_evaluation_rubric(self):
        judge = SeniorJudgeAgent()
        feedback = judge.evaluate(self.sample_findings)
        self.assertIsInstance(feedback, JudgeFeedback)
        self.assertGreaterEqual(feedback.accuracy_score, 1)
        self.assertLessEqual(feedback.accuracy_score, 10)
        self.assertGreaterEqual(feedback.overall_score, 1.0)
        self.assertLessEqual(feedback.overall_score, 10.0)
        self.assertTrue(feedback.pass_status)
        print(f"[Judge Audit Verified] Score: {feedback.overall_score}/10, Verdict: {feedback.pass_status}")

    def test_content_builder_curriculum_structure(self):
        builder = LeadContentBuilderAgent()
        feedback = JudgeFeedback(
            accuracy_score=9,
            language_parity_score=10,
            completeness_score=9,
            overall_score=9.3,
            pass_status=True,
            critique="Odlično strukturisan materijal.",
            missing_aspects=[],
        )
        course = builder.build_course(self.sample_findings, feedback, self.sample_youtube)

        # Must have exactly 7 sections
        self.assertEqual(len(course.sections), 7)
        self.assertTrue(course.sections[0].title.startswith("1. Uvod i Video Predavanje"))
        self.assertIn("[02:30]", course.sections[0].content_markdown)
        self.assertTrue(len(course.flashcards) >= 3)
        self.assertTrue(len(course.quiz) >= 1)
        self.assertTrue(course.verification_hash.startswith("ADK-VERIFIED-"))
        print(f"[Content Builder Verified] 7 sections produced with hash: {course.verification_hash}")


if __name__ == "__main__":
    unittest.main()
