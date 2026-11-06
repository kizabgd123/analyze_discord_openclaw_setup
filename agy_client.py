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

DEFAULT_AGY_ACCOUNT = os.getenv("AGY_ACCOUNT", "999@mrcleanervracar.com")

# Verified Antigravity Accounts with 999@mrcleanervracar.com as primary
AGY_ACCOUNTS: List[str] = [
    "999@mrcleanervracar.com",
    "glavni@mrcleanervracar.com",
    "promo@mrcleanervracar.com",
    "kiza101288@gmail.com",
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
    model: str = "claude-sonnet-4-6",
    account: str = "999@mrcleanervracar.com",
    timeout: int = 130,
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
    # Auto-fallback to claude-sonnet-4-6 if gemini individual quota is reached
    if ("RESOURCE_EXHAUSTED" in err or "quota reached" in err.lower()) and model != "claude-sonnet-4-6":
        logger.warning(f"[agy-cli] Kvota dostignuta za {model} na {account}. Pokrećem fallback na model claude-sonnet-4-6...")
        fallback_cmd = [
            AGY_BIN,
            "-p", full_prompt,
            "--model", "claude-sonnet-4-6",
            "--dangerously-skip-permissions",
            "--disable-slash-commands",
        ]
        fb_res = subprocess.run(
            fallback_cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd(),
            env=env,
        )
        fb_out = fb_res.stdout.strip()
        if fb_out:
            clean_lines = [
                re.sub(r"^[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]\s*Fetching available models\.\.\.", "", l).strip()
                for l in fb_out.splitlines()
            ]
            cleaned_fb = "\n".join([l for l in clean_lines if l]).strip()
            if cleaned_fb:
                logger.info(f"[agy-cli] claude-sonnet-4-6 model fallback uspešan na {account}")
                return cleaned_fb

    logger.warning(f"[agy-cli] Upozorenje/Greška za nalog {account} (kod {result.returncode}): {err}")
    if err and "error" not in err.lower() and "silent auth failed" not in err.lower():
        return err
    raise RuntimeError(f"Antigravity CLI error for {account} (kod {result.returncode}): {err}")


def query_agy_cli(
    prompt: str,
    system: Optional[str] = None,
    model: str = "claude-sonnet-4-6",
    account: Optional[str] = None,
    timeout: int = 130,
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

    # Allocate per-account timeout (strictly 130s so Claude/Gemini have time to respond)
    per_account_timeout = max(130, timeout)

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
