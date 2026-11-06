"""
unified_config.py — Centralized, Validated Configuration Module.
================================================================
Single source of truth for the Discord-OpenClaw AI OS.
Strictly adheres to backend-dev-guidelines:
- Zero raw `os.getenv` access across controllers, services, and routes.
- Schema-validated via Pydantic.
- Immutable config singleton exported as `unified_config` or `config`.
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env at the earliest initialization point
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class DiscordConfig(BaseModel):
    token: str = Field(
        default_factory=lambda: os.getenv("DISCORD_BOT_TOKEN", ""),
        description="Discord bot application token"
    )
    command_prefix: str = Field(
        default="!",
        description="Prefix for legacy text commands"
    )
    admin_user_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("ADMIN_DISCORD_USER_ID", None),
        description="Discord user ID authorized to approve Tier 2/3 actions"
    )
    auto_sync_tree: bool = Field(
        default=True,
        description="Whether to synchronize slash command tree on bot startup"
    )


class NLMConfig(BaseModel):
    binary_path: str = Field(
        default_factory=lambda: os.getenv("NLM_BIN", shutil.which("nlm") or "/home/kizamladjanijebac/.local/bin/nlm"),
        description="Path to official Google NotebookLM CLI binary"
    )
    default_notebook_id: str = Field(
        default_factory=lambda: os.getenv("NLM_NOTEBOOK_ID", "06da0502-7e35-4d6f-bf28-3de316dc0437"),
        description="Default fallback Google NotebookLM ID"
    )
    orchestration_notebook_id: str = Field(
        default="3bd81caf-9396-4593-ad18-4a98dc1a2115",
        description="Master orchestration knowledge notebook for Miki Nosonja"
    )
    timeout_seconds: float = Field(
        default=120.0,
        description="Default query timeout for NotebookLM"
    )


class AgyConfig(BaseModel):
    binary_path: str = Field(
        default_factory=lambda: os.getenv("AGY_BIN", shutil.which("agy") or "/home/kizamladjanijebac/.local/bin/agy"),
        description="Path to Antigravity CLI binary"
    )
    primary_account: str = Field(
        default_factory=lambda: os.getenv("AGY_ACCOUNT", "kiza101288@gmail.com"),
        description="Primary Antigravity account"
    )
    accounts: List[str] = Field(
        default=[
            "kiza101288@gmail.com",
            "promo@mrcleanervracar.com",
            "lovajetu@gmail.com",
            "lifemysolver@gmail.com",
        ],
        description="Verified accounts for Antigravity execution"
    )
    default_model: str = Field(
        default="gemini-3.8-flash-high",
        description="Default Antigravity LLM model"
    )
    fallback_model: str = Field(
        default="gemini-3.5-flash-lite",
        description="Sandbox fallback LLM model"
    )
    timeout_seconds: int = Field(
        default=150,
        description="CLI execution timeout"
    )


class DatabaseConfig(BaseModel):
    rag_db_path: Path = Field(
        default=PROJECT_ROOT / "antigravity_rag.db",
        description="Path to SQLite FTS5 RAG database"
    )
    openclaw_json_path: Path = Field(
        default=PROJECT_ROOT / "openclaw.json",
        description="Single source of truth OpenClaw config file"
    )
    debate_state_path: Path = Field(
        default=PROJECT_ROOT / "debate_state.json",
        description="Path to active debate state JSON"
    )
    memory_file: Path = Field(
        default=PROJECT_ROOT / "MEMORY.md",
        description="Path to shared cognitive memory file"
    )
    soul_file: Path = Field(
        default=PROJECT_ROOT / "SOUL.md",
        description="Path to agent soul/persona guidelines"
    )
    work_log_path: Path = Field(
        default=PROJECT_ROOT / "WORK_LOG.md",
        description="Path to immutable execution work log"
    )


class SentryObservabilityConfig(BaseModel):
    dsn: Optional[str] = Field(
        default_factory=lambda: os.getenv("SENTRY_DSN", None),
        description="Sentry project DSN for error reporting"
    )
    environment: str = Field(
        default_factory=lambda: os.getenv("APP_ENV", "production"),
        description="Operational runtime environment"
    )
    traces_sample_rate: float = Field(
        default=1.0,
        description="Performance tracing sample rate"
    )
    enabled: bool = Field(
        default_factory=lambda: os.getenv("SENTRY_ENABLED", "false").lower() in ("true", "1", "yes"),
        description="Flag to toggle Sentry instrumentation"
    )


class JudgeGuardConfig(BaseModel):
    secret: str = Field(
        default_factory=lambda: os.getenv("JUDGE_HMAC_SECRET", "openclaw-dev-secret-change-me"),
        description="HMAC verification key for action authorization"
    )
    freshness_window_seconds: int = Field(
        default=300,
        description="Window limit in seconds for WORK_LOG mtime freshness"
    )


class UnifiedConfig(BaseModel):
    project_name: str = "discord-openclaw"
    version: str = "2.0.0"
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    nlm: NLMConfig = Field(default_factory=NLMConfig)
    agy: AgyConfig = Field(default_factory=AgyConfig)
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    observability: SentryObservabilityConfig = Field(default_factory=SentryObservabilityConfig)
    judge_guard: JudgeGuardConfig = Field(default_factory=JudgeGuardConfig)


# Singleton instance
unified_config = UnifiedConfig()
config = unified_config
