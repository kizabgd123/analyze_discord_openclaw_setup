"""Zero-Mock Verification Suite: YouTube Discovery & Shared Schemas.
Tests real live oEmbed HTTP responses and Pydantic validation contracts.
"""

import sys
import unittest
from a2a_lms.shared.schemas import Chapter, YouTubeMetadata, JudgeFeedback, Flashcard, QuizQuestion
from a2a_lms.shared.youtube_lookup import (
    extract_head_entity,
    build_query_hierarchy,
    verify_oembed,
    extract_chapters_from_description,
    find_embeddable_youtube_video,
)


class TestYouTubeDiscoveryAndSchemas(unittest.TestCase):
    """Zero-mock tests verifying live endpoints and strict schema contracts."""

    def test_head_entity_extraction_and_cleaning(self):
        # Delimiter split and noise removal
        e1 = extract_head_entity("OpenClaw: Automatizacija i Bezbednosna Analiza")
        self.assertEqual(e1, "openclaw")

        # Serbian domain translation
        e2 = extract_head_entity("Stoni tenis - Bekhend top-spin protiv rezane lopte")
        self.assertEqual(e2, "table tennis")

        # Fluff stripping + AI translation
        e3 = extract_head_entity("Vodič kroz veštačku inteligenciju")
        self.assertEqual(e3, "artificial intelligence")

    def test_query_relaxation_hierarchy(self):
        queries = build_query_hierarchy("google adk multi agent")
        self.assertEqual(len(queries), 4)
        self.assertEqual(queries[0], "google adk multi agent tutorial")
        self.assertEqual(queries[1], "google adk multi agent crash course")
        self.assertEqual(queries[2], "google adk multi tutorial")
        self.assertEqual(queries[3], "google adk multi agent")

    def test_chapter_parsing(self):
        sample_desc = """
        00:00 - Introduction to Agents
        02:15 - Setting up Environment
        05:40 - Multi-Agent Communication
        """
        chapters = extract_chapters_from_description(sample_desc, 600)
        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0].seconds, 0)
        self.assertEqual(chapters[0].title, "Introduction to Agents")
        self.assertEqual(chapters[1].seconds, 135)
        self.assertEqual(chapters[2].seconds, 340)

    def test_live_oembed_verification_zero_mock(self):
        """Perform authentic live HTTP oEmbed check on verified YouTube video."""
        # u4ydH-QvPeg is Adrian Twarog's verified video referenced in NotebookLM
        ok, data = verify_oembed("u4ydH-QvPeg")
        self.assertTrue(ok, "Live oEmbed HTTP check must succeed for verified video")
        self.assertIsNotNone(data)
        self.assertIn("author_name", data)
        print(f"[Zero-Mock Check] Live oEmbed confirmed for: {data.get('title')} by {data.get('author_name')}")

    def test_video_discovery_failsafe_resolution(self):
        meta = find_embeddable_youtube_video("Stoni tenis za početnike", domain_type="sports")
        self.assertIsInstance(meta, YouTubeMetadata)
        self.assertTrue(meta.verified)
        self.assertTrue(len(meta.chapters) >= 4)
        self.assertTrue(meta.embed_url.startswith("https://www.youtube-nocookie.com/embed/"))

    def test_judge_feedback_schema_contract(self):
        feedback = JudgeFeedback(
            accuracy_score=9,
            language_parity_score=10,
            completeness_score=8,
            overall_score=9.0,
            pass_status=True,
            critique="Izuzetno činjenično precizan sadržaj na čistom srpskom jeziku.",
            missing_aspects=[],
        )
        self.assertTrue(feedback.pass_status)
        self.assertGreaterEqual(feedback.overall_score, 7.0)

    def test_quiz_question_schema_constraints(self):
        q = QuizQuestion(
            question="Šta definiše A2A protokol?",
            options=[
                "Direktnu komunikaciju između agenata",
                "Monolitnu bazu podataka",
                "Samo jedan LLM model",
                "Isključivo REST web interfejs"
            ],
            correct_index=0,
            explanation="A2A omogućava autonomnu razmenu stanja i zadataka između agenata."
        )
        self.assertEqual(len(q.options), 4)
        self.assertEqual(q.correct_index, 0)


if __name__ == "__main__":
    unittest.main()
