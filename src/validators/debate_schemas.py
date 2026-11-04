"""
debate_schemas.py — Validation Schemas for Multi-Agent Debate & ADK Orchestration.
==================================================================================
"""

from typing import Optional, Dict
from pydantic import BaseModel, Field, field_validator


class StartDebateSchema(BaseModel):
    topic: str = Field(..., min_length=3, max_length=1500, description="Debate topic or ADK task")
    rounds: int = Field(default=2, ge=1, le=5, description="Number of debate rounds (1 to 5)")
    custom_notebooks: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional custom notebook mapping per persona"
    )

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 3:
            raise ValueError("Topic must contain at least 3 characters")
        return cleaned


class ActionApprovalSchema(BaseModel):
    action: str = Field(..., min_length=1, description="Command or proposed action string")
    approver_id: str = Field(..., description="Discord user ID attempting authorization")
    tier: int = Field(default=2, ge=1, le=3, description="Risk tier: 1=Read-only, 2=State, 3=Critical")
