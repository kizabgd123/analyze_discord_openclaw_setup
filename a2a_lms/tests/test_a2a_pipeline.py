"""Zero-Mock End-to-End Integration Test for A2A Multi-Agent LMS Pipeline.
Tests FastAPI endpoints, live healthcheck, and full orchestrator curriculum generation.
"""

import asyncio
import unittest
from fastapi.testclient import TestClient
from a2a_lms.app.main import app
from a2a_lms.agents.orchestrator.agent import LMSOrchestrator
from a2a_lms.shared.schemas import CoursePayload


class TestA2APipelineE2E(unittest.TestCase):
    """End-to-end integration test verifying zero-mock constraints and full pipeline."""

    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        """Verify API health status and brain ID."""
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["engine"], "google-adk-2.0-a2a")
        self.assertTrue(data["zero_mock_enforced"])
        self.assertEqual(data["notebook_brain_id"], "9c8878e1-1fb4-4035-b022-7678a10be7f3")

    def test_static_frontend_serving(self):
        """Verify that index.html and course.html are cleanly served."""
        resp_index = self.client.get("/")
        self.assertEqual(resp_index.status_code, 200)
        self.assertIn("Google ADK A2A Multi-Agent LMS", resp_index.text)

        resp_course = self.client.get("/course.html")
        self.assertEqual(resp_course.status_code, 200)
        self.assertIn("Masterclass Lekcija", resp_course.text)

    def test_orchestrator_live_e2e_run(self):
        """Execute complete orchestrator pipeline with live grounded brain."""
        orchestrator = LMSOrchestrator(notebook_id="9c8878e1-1fb4-4035-b022-7678a10be7f3")
        progress_events = []

        def on_progress(msg: str):
            progress_events.append(msg)
            print(f"[E2E Progress] {msg}")

        topic = "Google ADK A2A Multi-Agent Sistemi 2026"
        course: CoursePayload = asyncio.run(orchestrator.run(topic=topic, on_progress=on_progress))

        # Assertions on final CoursePayload
        self.assertIsInstance(course, CoursePayload)
        self.assertEqual(course.topic, topic)
        self.assertEqual(course.language, "sr")

        # 1. YouTube discovery checks
        self.assertTrue(course.youtube_metadata.verified)
        self.assertTrue(course.youtube_metadata.embed_url.startswith("https://www.youtube-nocookie.com/embed/"))
        self.assertGreaterEqual(len(course.youtube_metadata.chapters), 3)

        # 2. Judge evaluation checks
        self.assertTrue(course.judge_feedback.pass_status)
        self.assertGreaterEqual(course.judge_feedback.overall_score, 7.0)

        # 3. 7 Masterclass Sections check
        self.assertEqual(len(course.sections), 7)
        expected_sections = [
            "1. Uvod i Video Predavanje",
            "2. Ključni Principi i Mehanika",
            "3. Korak-po-Korak Tehnika i Primena",
            "4. Česte Greške i Zablude",
            "5. Praktični Izazov i Trening Plan",
            "6. Provera Znanja i Interaktivni Kviz",
            "7. Brzi Priručnik i Rezime",
        ]
        for idx, title_prefix in enumerate(expected_sections, 1):
            self.assertEqual(course.sections[idx - 1].index, idx)
            self.assertTrue(
                course.sections[idx - 1].title.startswith(title_prefix),
                f"Section {idx} title mismatch: {course.sections[idx - 1].title}"
            )

        # 4. Interactive 3D Flashcards & Quiz checks
        self.assertGreaterEqual(len(course.flashcards), 3)
        self.assertGreaterEqual(len(course.quiz), 1)
        self.assertEqual(len(course.quiz[0].options), 4)

        # 5. Verification hash check
        self.assertTrue(course.verification_hash.startswith("ADK-VERIFIED-"))
        self.assertTrue(len(progress_events) >= 4)
        print(f"\n[E2E Zero-Mock Verification SUCCESSFUL] Verification Hash: {course.verification_hash}\n")


if __name__ == "__main__":
    unittest.main()
