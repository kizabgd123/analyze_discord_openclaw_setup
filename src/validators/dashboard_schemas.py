"""
dashboard_schemas.py — Validation Schemas for Data App & Dashboard Operations.
==============================================================================
Provides input validation for dashboard REST endpoints and SSE chat requests.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class DashboardChatRequestSchema(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000, description="Korisnička poruka za Data Chat")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Istorijat prethodnih poruka")
    provider: Optional[str] = Field("auto", description="Model provider ('auto', 'litert', 'gemini')")

    @field_validator("message")
    @classmethod
    def strip_message(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Poruka ne može biti prazna.")
        return cleaned


class RAGSearchRequestSchema(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000, description="Pretraga za lokalni RAG indeks")
    limit: int = Field(5, ge=1, le=50, description="Maksimalan broj rezultata")

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Upit za pretragu ne može biti prazan.")
        return cleaned
