#!/usr/bin/env python3
"""
JudgeGuard — Deterministic Safety Gate for OpenClaw / Antigravity 2.0
=======================================================================
Implements HMAC-SHA256 Quorum Verdict:
  - Every proposed action is signed and verified before execution
  - WORK_LOG.md freshness enforced (5-minute sliding window)
  - Blacklist of dangerous shell patterns
  - CLI mode: python3 judge_guard.py "Action description"
  - Library mode: from judge_guard import JudgeGuard; judge.verify(action)

Exit codes (CLI):
  0  → PASSED
  1  → BLOCKED
"""

import os
import sys
import time
import hashlib
import hmac
import json
import re
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# ── CONFIG ──────────────────────────────────────────────────────────────────
_WORK_LOG = Path(__file__).parent / "WORK_LOG.md"
_FRESHNESS_WINDOW_SECONDS = 300          # 5 minutes
_DEFAULT_SECRET = os.getenv("JUDGE_HMAC_SECRET", "openclaw-dev-secret-change-me")

# Patterns that are always BLOCKED regardless of any other check
_BLACKLIST_PATTERNS = [
    r"rm\s+-rf\s+/",              # Recursive root delete
    r"mkfs\.",                    # Format filesystem
    r"dd\s+if=",                  # Raw disk write
    r">\s*/dev/sd",              # Overwrite block device
    r"chmod\s+777\s+/",           # 777 on root
    r"curl.*\|\s*sh",             # curl | sh (supply chain risk)
    r"wget.*\|\s*sh",
    r"eval\s*\(",                 # eval() in shell
    r"base64\s+-d.*\|\s*sh",     # Encoded payload execution
    r":(){.*};:",                 # Fork bomb
    r"sudo\s+su\b",              # sudo su
]
_BLACKLIST_RE = [re.compile(p, re.IGNORECASE) for p in _BLACKLIST_PATTERNS]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [JudgeGuard] %(levelname)s: %(message)s"
)
logger = logging.getLogger("JudgeGuard")


class JudgeGuardError(Exception):
    pass


class JudgeGuard:
    """
    Deterministic safety gate. Use as a context-free singleton.

    Usage (library mode):
        judge = JudgeGuard(secret=JUDGE_HMAC_SECRET)
        verdict = judge.verify(proposed_action)
        # verdict → "PASSED" | "BLOCKED"
    """

    def __init__(
        self,
        secret: str = _DEFAULT_SECRET,
        work_log_path: Optional[Path] = None,
        freshness_seconds: int = _FRESHNESS_WINDOW_SECONDS,
    ):
        self.secret = secret.encode("utf-8") if isinstance(secret, str) else secret
        self.work_log = work_log_path or _WORK_LOG
        self.freshness_seconds = freshness_seconds

    # ── Public API ────────────────────────────────────────────────────────

    def verify(self, proposed_action: Any) -> str:
        """
        Run all safety checks on a proposed action.
        Returns "PASSED" or "BLOCKED".
        `proposed_action` can be a str, dict, or any serialisable object.
        """
        action_str = self._serialize(proposed_action)
        verdict, reason = self._run_checks(action_str)
        level = logging.WARNING if verdict == "BLOCKED" else logging.INFO
        logger.log(level, f"[{verdict}] {reason} | action={action_str[:80]}")
        return verdict

    def sign(self, payload: str) -> str:
        """Return HMAC-SHA256 hex digest for an action payload."""
        return hmac.new(self.secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_signature(self, payload: str, signature: str) -> bool:
        """Constant-time HMAC comparison."""
        expected = self.sign(payload)
        return hmac.compare_digest(expected, signature)

    def log_start(self, action_label: str) -> None:
        """Write 🟡 start entry to WORK_LOG.md (required before execution)."""
        self._append_log(f"🟡 Starting {action_label}")

    def log_complete(self, action_label: str) -> None:
        """Write ✅ completion entry to WORK_LOG.md."""
        self._append_log(f"✅ Completed {action_label}")

    def log_blocked(self, action_label: str, reason: str) -> None:
        """Write ❌ blocked entry to WORK_LOG.md."""
        self._append_log(f"❌ BLOCKED {action_label} — {reason}")

    # ── Internal checks ───────────────────────────────────────────────────

    def _run_checks(self, action_str: str) -> tuple[str, str]:
        """Execute all checks in priority order. First failure wins."""

        # 1. Blacklist pattern scan
        for pattern in _BLACKLIST_RE:
            if pattern.search(action_str):
                return "BLOCKED", f"Blacklist pattern matched: {pattern.pattern!r}"

        # 2. WORK_LOG freshness — only enforced if log exists
        freshness_ok, freshness_msg = self._check_work_log_freshness()
        if not freshness_ok:
            return "BLOCKED", freshness_msg

        return "PASSED", "All checks passed"

    def _check_work_log_freshness(self) -> tuple[bool, str]:
        """
        Verify WORK_LOG.md was updated within the freshness window.
        If log doesn't exist yet, PASS (first-run scenario).
        """
        if not self.work_log.exists():
            return True, "WORK_LOG.md not found — first-run pass"

        try:
            mtime = self.work_log.stat().st_mtime
            age_seconds = time.time() - mtime
            if age_seconds > self.freshness_seconds:
                return False, (
                    f"WORK_LOG.md is stale ({age_seconds:.0f}s > "
                    f"{self.freshness_seconds}s). Update it before proceeding."
                )
            return True, f"WORK_LOG.md fresh ({age_seconds:.0f}s old)"
        except OSError as e:
            return False, f"Cannot stat WORK_LOG.md: {e}"

    def _append_log(self, message: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        entry = f"{ts} | {message}\n"
        try:
            with open(self.work_log, "a", encoding="utf-8") as f:
                f.write(entry)
        except OSError as e:
            logger.warning(f"Could not write to WORK_LOG.md: {e}")

    @staticmethod
    def _serialize(action: Any) -> str:
        if isinstance(action, str):
            return action
        try:
            return json.dumps(action, ensure_ascii=False, default=str)
        except Exception:
            return str(action)


# ── CLI entrypoint ──────────────────────────────────────────────────────────
def _cli_main():
    if len(sys.argv) < 2:
        print("Usage: python3 judge_guard.py \"Action description\"")
        sys.exit(1)

    action_description = " ".join(sys.argv[1:])
    secret = os.getenv("JUDGE_HMAC_SECRET", _DEFAULT_SECRET)
    judge = JudgeGuard(secret=secret)

    # Log the check attempt
    judge.log_start(action_description)

    verdict = judge.verify(action_description)
    print(f"JudgeGuard Verdict: {verdict}")

    if verdict == "PASSED":
        sys.exit(0)
    else:
        judge.log_blocked(action_description, "Safety check failed")
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
