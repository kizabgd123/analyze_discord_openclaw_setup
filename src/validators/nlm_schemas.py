"""
nlm_schemas.py — Input Validation Schemas for NotebookLM Operations.
===================================================================
Enforces Zod/Pydantic validation rule: No unvalidated external input.
"""

from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class AskQuerySchema(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="User question prompt")
    notebook_id: Optional[str] = Field(default=None, description="Target Google NotebookLM ID")

    @field_validator("query")
    @classmethod
    def strip_and_clean_query(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Query cannot be empty or whitespace only")
        return cleaned


class AddNoteSchema(BaseModel):
    text: str = Field(..., min_length=1, max_length=50000, description="Note body content")
    title: Optional[str] = Field(default=None, max_length=200, description="Optional note title")
    notebook_id: Optional[str] = Field(default=None, description="Target Google NotebookLM ID")


class AddUrlSchema(BaseModel):
    url: HttpUrl = Field(..., description="Valid web URL or YouTube link to ingest")
    notebook_id: Optional[str] = Field(default=None, description="Target Google NotebookLM ID")


class SelectNotebookSchema(BaseModel):
    notebook_id: str = Field(..., min_length=1, max_length=100, description="Google NotebookLM ID")
    channel_id: Optional[int] = Field(default=None, description="Discord Channel ID context")
