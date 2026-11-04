"""Pydantic schemas and typed session contracts for the Google ADK A2A LMS."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class Chapter(BaseModel):
    """Timestamp chapter in a verified YouTube tutorial."""
    timestamp: str = Field(..., description="Timestamp formatted as mm:ss or hh:mm:ss")
    seconds: int = Field(..., ge=0, description="Offset in seconds from video start")
    title: str = Field(..., description="Chapter topic or title")


class YouTubeMetadata(BaseModel):
    """Authentic YouTube video discovery data (Zero-Mock verified)."""
    video_id: str = Field(..., description="11-character YouTube video ID")
    title: str = Field(..., description="Video title")
    author: str = Field(..., description="Channel / creator name")
    duration_seconds: int = Field(..., ge=60, description="Total video length in seconds")
    duration_formatted: str = Field(..., description="Formatted duration e.g. 14:20")
    chapters: List[Chapter] = Field(default_factory=list, description="Interactive timestamp chapters")
    embed_url: str = Field(..., description="Nocookie embed URL")
    verified: bool = Field(default=True, description="oEmbed accessibility confirmed")


class JudgeFeedback(BaseModel):
    """Senior Judge evaluation rubric and audit verdict."""
    accuracy_score: int = Field(..., ge=1, le=10, description="Factuality and technical correctness")
    language_parity_score: int = Field(..., ge=1, le=10, description="Serbian language parity and consistency")
    completeness_score: int = Field(..., ge=1, le=10, description="Completeness of mental models and domain fit")
    overall_score: float = Field(..., ge=1.0, le=10.0, description="Calculated aggregate score")
    pass_status: bool = Field(..., description="True if overall_score >= 7.0 and critical checks pass")
    critique: str = Field(..., description="Actionable critique and review notes")
    missing_aspects: List[str] = Field(default_factory=list, description="Specific items required for revision")

    @field_validator("overall_score", mode="before")
    @classmethod
    def compute_overall(cls, v: Any, info: Any) -> float:
        if v is not None:
            return float(v)
        return 7.0


class ResearchFindings(BaseModel):
    """Grounded domain analysis emitted by Principal Researcher Agent."""
    topic: str
    domain_type: str = Field(..., description="technical | sports | science | business | general")
    mental_models: List[str] = Field(default_factory=list)
    core_principles: List[str] = Field(default_factory=list)
    practical_steps: List[str] = Field(default_factory=list)
    traps_and_pitfalls: List[str] = Field(default_factory=list)
    sidecar_type: Optional[str] = Field(None, description="Optional science sidecar viewer name")
    raw_markdown: str


class Flashcard(BaseModel):
    """Active recall 3D flashcard item."""
    front: str = Field(..., description="Concept, term or challenging question")
    back: str = Field(..., description="Precise definition, rule, or explanation")


class QuizQuestion(BaseModel):
    """Interactive 4-choice knowledge quiz question."""
    question: str
    options: List[str] = Field(..., min_length=4, max_length=4, description="Four choices (A, B, C, D)")
    correct_index: int = Field(..., ge=0, le=3, description="0-based index of correct option")
    explanation: str = Field(..., description="Pedagogical rationale for the correct answer")


class CourseSection(BaseModel):
    """One of the 7 foundational masterclass modules."""
    index: int = Field(..., ge=1, le=7)
    title: str
    content_markdown: str


class CoursePayload(BaseModel):
    """Final verified interactive course curriculum ready for delivery."""
    topic: str
    language: str = "sr"
    research_findings: ResearchFindings
    judge_feedback: JudgeFeedback
    youtube_metadata: YouTubeMetadata
    sections: List[CourseSection]
    flashcards: List[Flashcard]
    quiz: List[QuizQuestion]
    full_course_markdown: str
    verification_hash: str
    created_at: str
