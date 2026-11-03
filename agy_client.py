#!/usr/bin/env python3
"""
agy_client.py — Antigravity CLI Client with Account Rotation.
============================================================
Dedicated runner for Miki Nosonja (the Master Orchestrator):
  1. Executes prompts using the official Antigravity CLI (`agy`).
  2. Rotates between the 4 verified user accounts via AGY_ACCOUNT.
  3. Uses models: `gemini-3.8-flash-high` (default), `claude-sonnet-4-6`, etc.
"""

import os
import sys
import logging
import subprocess
import shutil
import re
from typing import Optional, List

logger = logging.getLogger("AgyClient")

AGY_BIN = os.getenv("AGY_BIN", shutil.which("agy") or "/home/kizamladjanijebac/.local/bin/agy")

# 4 Verified Antigravity Accounts from workspace configuration
AGY_ACCOUNTS: List[str] = [
    "promo@mrcleanervracar.com",
    "kiza101288@gmail.com",
    "lovajetu@gmail.com",
    "lifemysolver@gmail.com",
]

_current_account_idx = 0


def get_next_agy_account() -> str:
    """Rotates to the next verified Antigravity account."""
    global _current_account_idx
    account = AGY_ACCOUNTS[_current_account_idx % len(AGY_ACCOUNTS)]
    _current_account_idx += 1
    return account


def query_agy_cli(
    prompt: str,
    system: Optional[str] = None,
    model: str = "gemini-3.8-flash-high",
    account: Optional[str] = None,
    timeout: int = 150,
) -> str:
    """
    Executes a query via antigravity-cli (`agy`) in print mode (-p).
    Used exclusively by Miki Nosonja to organize agents and synthesize final answers.
    """
    if not os.path.exists(AGY_BIN):
        raise FileNotFoundError(f"Antigravity CLI binarni fajl nije pronađen na {AGY_BIN}")

    selected_account = account or get_next_agy_account()
    full_prompt = f"Instrukcija: {system}\n\nZadatak: {prompt}" if system else prompt

    cmd = [
        AGY_BIN,
        "-p", full_prompt,
        "--model", model,
        "--dangerously-skip-permissions",
        "--disable-slash-commands",
    ]

    env = os.environ.copy()
    env["AGY_ACCOUNT"] = selected_account

    logger.info(f"[Miki Nosonja / agy-cli] Pokrećem agy CLI | nalog={selected_account} | model={model}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd(),
            env=env,
        )

        output = result.stdout.strip()
        if output:
            # Clean possible TUI spinner artifacts like ⠋, ⠙, ⠹, etc.
            clean_lines = []
            for line in output.splitlines():
                stripped = re.sub(r"^[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]\s*Fetching available models\.\.\.", "", line).strip()
                if stripped:
                    clean_lines.append(stripped)
            cleaned = "\n".join(clean_lines).strip()
            if cleaned:
                return cleaned

        err = result.stderr.strip()
        logger.warning(f"[agy-cli] Upozorenje/Greška (kod {result.returncode}): {err}")
        if err and "error" not in err.lower():
            return err
        raise RuntimeError(f"Antigravity CLI error (kod {result.returncode}): {err}")

    except subprocess.TimeoutExpired:
        logger.error(f"[agy-cli] Timeout nakon {timeout}s za nalog {selected_account}")
        raise TimeoutError(f"Antigravity CLI je istekao nakon {timeout}s")


if __name__ == "__main__":
    print(f"AGY BIN: {AGY_BIN}")
    print(f"Verified Accounts: {AGY_ACCOUNTS}")
