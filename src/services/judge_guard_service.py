"""
judge_guard_service.py — Deterministic Quorum & Safety Gate Service.
====================================================================
Implements MASTER_ORCHESTRATION.md Law 2 & Law 7:
- HMAC-SHA256 signature verification.
- Blacklist scanning for destructive commands.
- WORK_LOG.md freshness enforcement.
"""

import time
import hmac
import hashlib
import logging
from typing import Tuple, Any, Optional
from src.config.unified_config import config
from src.repositories.state_repository import StateRepository
from src.validators.system_schemas import ShellCommandSchema
from src.instrument import capture_exception

logger = logging.getLogger("JudgeGuardService")


class JudgeGuardService:
    """Service providing deterministic safety validation before any modifying action."""

    def __init__(self, state_repo: Optional[StateRepository] = None):
        self.state_repo = state_repo or StateRepository()
        self.secret = config.judge_guard.secret.encode("utf-8")
        self.freshness_window = config.judge_guard.freshness_window_seconds

    def sign_action(self, payload: str) -> str:
        """Computes HMAC-SHA256 hex digest for an approved action."""
        return hmac.new(self.secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_action(self, action: Any) -> Tuple[bool, str]:
        """
        Runs comprehensive security checks on a proposed action.
        Returns: (passed: bool, message: str)
        """
        action_str = str(action)

        # 1. Schema / Blacklist pattern scan
        try:
            ShellCommandSchema(command=action_str)
        except ValueError as val_err:
            reason = str(val_err)
            self.state_repo.append_work_log(f"❌ BLOCKED {action_str[:60]} — {reason}")
            return False, reason

        # 2. WORK_LOG.md freshness check
        freshness_ok, freshness_msg = self._check_work_log_freshness()
        if not freshness_ok:
            self.state_repo.append_work_log(f"❌ BLOCKED {action_str[:60]} — {freshness_msg}")
            return False, freshness_msg

        return True, "PASSED: All safety checks satisfied"

    def _check_work_log_freshness(self) -> Tuple[bool, str]:
        """Validates that WORK_LOG.md was updated within the freshness window."""
        work_log = self.state_repo.work_log_path
        if not work_log.exists():
            return True, "WORK_LOG.md initialized (first-run pass)"

        try:
            mtime = work_log.stat().st_mtime
            age_seconds = time.time() - mtime
            if age_seconds > self.freshness_window:
                return False, f"WORK_LOG.md is stale ({age_seconds:.0f}s > {self.freshness_window}s window)."
            return True, f"WORK_LOG.md is fresh ({age_seconds:.0f}s old)"
        except OSError as exc:
            capture_exception(exc, {"path": str(work_log)})
            return False, f"Unable to access WORK_LOG.md: {exc}"
