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

DEFAULT_AGY_ACCOUNT = os.getenv("AGY_ACCOUNT", "kiza101288@gmail.com")

# Verified Antigravity Accounts with kiza101288@gmail.com as primary
AGY_ACCOUNTS: List[str] = [
    "kiza101288@gmail.com",
    "promo@mrcleanervracar.com",
    "lovajetu@gmail.com",
    "lifemysolver@gmail.com",
    "stojanoviczoran887@gmail.com",
]

_current_account_idx = 0


def get_next_agy_account() -> str:
    """Rotates to the next verified Antigravity account."""
    global _current_account_idx
    account = AGY_ACCOUNTS[_current_account_idx % len(AGY_ACCOUNTS)]
    _current_account_idx += 1
    return account


def _execute_single_agy_run(
    prompt: str,
    system: Optional[str] = None,
    model: str = "gemini-3.8-flash-high",
    account: str = "kiza101288@gmail.com",
    timeout: int = 45,
) -> str:
    """Runs a single prompt under a specific Antigravity account."""
    if not os.path.exists(AGY_BIN):
        raise FileNotFoundError(f"Antigravity CLI binarni fajl nije pronađen na {AGY_BIN}")

    full_prompt = f"Instrukcija: {system}\n\nZadatak: {prompt}" if system else prompt

    cmd = [
        AGY_BIN,
        "-p", full_prompt,
        "--model", model,
        "--dangerously-skip-permissions",
        "--disable-slash-commands",
    ]

    env = os.environ.copy()
    env["AGY_ACCOUNT"] = account

    logger.info(f"[agy-cli] Pokrećem agy CLI | nalog={account} | model={model} | timeout={timeout}s")

    result = subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL,
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
    logger.warning(f"[agy-cli] Upozorenje/Greška za nalog {account} (kod {result.returncode}): {err}")
    if err and "error" not in err.lower() and "silent auth failed" not in err.lower():
        return err
    raise RuntimeError(f"Antigravity CLI error for {account} (kod {result.returncode}): {err}")


def query_agy_cli(
    prompt: str,
    system: Optional[str] = None,
    model: str = "gemini-3.8-flash-high",
    account: Optional[str] = None,
    timeout: int = 150,
    auto_failover: bool = True,
) -> str:
    """
    Executes a query via antigravity-cli (`agy`) in print mode (-p).
    Supports automatic multi-account failover across verified accounts
    if an account encounters timeout or silent auth failure.
    """
    primary_account = account or DEFAULT_AGY_ACCOUNT
    candidate_accounts = [primary_account]
    if auto_failover:
        for acc in AGY_ACCOUNTS:
            if acc not in candidate_accounts:
                candidate_accounts.append(acc)

    # Allocate per-account timeout (min 35s per candidate attempt, max total timeout)
    per_account_timeout = max(35, min(60, timeout // max(1, len(candidate_accounts))))

    last_error: Optional[Exception] = None
    for acc in candidate_accounts:
        try:
            res = _execute_single_agy_run(
                prompt=prompt,
                system=system,
                model=model,
                account=acc,
                timeout=per_account_timeout,
            )
            if res and len(res.strip()) > 0:
                logger.info(f"[agy-cli] Uspešno izvršen upit | aktivan nalog={acc}")
                return res
        except (subprocess.TimeoutExpired, TimeoutError) as t_err:
            last_error = t_err
            logger.warning(f"[agy-cli] Timeout ({per_account_timeout}s) za nalog {acc}. Pokušavam sledeći nalog...")
        except Exception as e:
            last_error = e
            logger.warning(f"[agy-cli] Greška za nalog {acc}: {e}. Pokušavam sledeći nalog...")

    if last_error:
        raise last_error
    raise RuntimeError("Nijedan Antigravity nalog nije uspeo da vrati odgovor.")


if __name__ == "__main__":
    print(f"AGY BIN: {AGY_BIN}")
    print(f"Verified Accounts: {AGY_ACCOUNTS}")
