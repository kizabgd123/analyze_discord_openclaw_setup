"""
litert_schemas.py — Validation Schemas for LiteRT & Local Model Operations.
===========================================================================
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class LiteRTChatSchema(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000, description="Korisnički upit za LiteRT agenta")
    system_instructions: Optional[str] = Field(None, max_length=5000, description="Opcione sistemske instrukcije")
    workspace_dir: Optional[str] = Field(None, description="Putanja do lokalnog radnog prostora")
    use_external_server: bool = Field(False, description="Da li se koristi eksterni OpenAI-kompatibilni server")

    @field_validator("prompt")
    @classmethod
    def strip_prompt(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Upit ne može biti prazan.")
        return cleaned


class LiteRTConfigUpdateSchema(BaseModel):
    backend: Optional[str] = Field(None, description="Backend ('gpu', 'npu', 'cpu', 'auto')")
    enable_speculative_decoding: Optional[bool] = Field(None, description="Spekulativno dekodovanje")
    model_path: Optional[str] = Field(None, description="Putanja do modela")

    @field_validator("backend")
    @classmethod
    def validate_backend(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        cleaned = v.lower().strip()
        if cleaned not in ("gpu", "npu", "cpu", "auto"):
            raise ValueError(f"Nepoznat backend: {v}. Dozvoljeni: gpu, npu, cpu, auto")
        return cleaned
