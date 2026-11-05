"""
system_schemas.py — Validation Schemas for System & Shell Operations.
=====================================================================
"""

import re
from pydantic import BaseModel, Field, field_validator

# Immutable blacklist patterns per MASTER_ORCHESTRATION.md Law 7 (synced with judge_guard.py)
_BLOCKED_COMMAND_PATTERNS = [
    re.compile(r"rm\s+-rf\s+/", re.IGNORECASE),
    re.compile(r"mkfs\.", re.IGNORECASE),
    re.compile(r"dd\s+if=", re.IGNORECASE),
    re.compile(r">\s*/dev/sd", re.IGNORECASE),
    re.compile(r"chmod\s+777\s+/", re.IGNORECASE),
    re.compile(r"curl.*\|\s*sh", re.IGNORECASE),
    re.compile(r"wget.*\|\s*sh", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"base64\s+-d.*\|\s*sh", re.IGNORECASE),
    re.compile(r":\(\)\s*\{\s*:\|\:&\s*\};:", re.IGNORECASE),
    re.compile(r":\(\)\s*\{.*\}\s*;:", re.IGNORECASE),
    re.compile(r"sudo\s+su\b", re.IGNORECASE),
]


class ShellCommandSchema(BaseModel):
    command: str = Field(..., min_length=1, max_length=1000, description="Shell command string")

    @field_validator("command")
    @classmethod
    def check_safety_blacklist(cls, v: str) -> str:
        cmd = v.strip()
        if not cmd:
            raise ValueError("Command cannot be empty")
        for pattern in _BLOCKED_COMMAND_PATTERNS:
            if pattern.search(cmd):
                raise ValueError(f"Dangerous operation rejected: pattern {pattern.pattern} is strictly prohibited")
        return cmd
