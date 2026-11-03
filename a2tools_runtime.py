#!/usr/bin/env python3
"""
a2tools_runtime.py — Strict Tool Execution Runtime for OpenClaw ADK.
===================================================================
Enforces the Zero-Mock / Zero-Simulation policy:
  - NotebookLM queries are executed strictly via the official `nlm` CLI.
  - IF NotebookLM cannot be reached or fails, it emits an explicit ERROR and HALTS.
  - NO local fallback guessing, NO dummy stubs.
  - State-changing operations must pass JudgeGuard Quorum.
"""

import os
import sys
import json
import asyncio
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("A2Tools")

NLM_BIN = shutil.which("nlm") or "/home/kizamladjanijebac/.local/bin/nlm"
ORCHESTRATION_NOTEBOOK_ID = "3bd81caf-9396-4593-ad18-4a98dc1a2115"
ADK_A2A_NOTEBOOK_ID = "8347bceb-fc45-4a38-80d2-d774a06e6669"
HILL_CLIMBING_NOTEBOOK_ID = "74c1293b-1c49-484c-96f1-b96aa8703416"


@dataclass
class ToolExecutionResult:
    success: bool
    output: str
    error_type: Optional[str] = None
    is_error: bool = False
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error_type": self.error_type,
            "is_error": self.is_error,
            "metadata": self.metadata or {},
        }


class A2ToolsRuntime:
    """Manages verified tools execution for Google ADK agents."""

    def __init__(self, nlm_bin: str = NLM_BIN):
        self.nlm_bin = nlm_bin

    def _get_nlm_env(self) -> Dict[str, str]:
        """Loads refreshed credentials from ~/.nlm/env."""
        env = os.environ.copy()
        nlm_env_file = os.path.expanduser("~/.nlm/env")
        if os.path.exists(nlm_env_file):
            try:
                with open(nlm_env_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("export "):
                            line = line[7:]
                        if "=" in line:
                            k, v = line.split("=", 1)
                            env[k] = v.strip('"\'')
            except Exception as e:
                logger.warning(f"Could not read ~/.nlm/env: {e}")
        return env

    async def query_notebooklm(
        self,
        notebook_id: str,
        query: str,
        timeout: float = 120.0,
    ) -> ToolExecutionResult:
        """Executes a real Google NotebookLM grounded query via `nlm` CLI.

        CRITICAL RULE:
        If NotebookLM cannot be fetched or returns an error, this method returns
        an explicit error without any local simulation or fallback guessing.
        """
        if not query or len(query.strip()) < 3:
            return ToolExecutionResult(
                success=False,
                output="GREŠKA: Upit mora imati najmanje 3 karaktera.",
                error_type="validation_error",
                is_error=True,
            )

        if not os.path.exists(self.nlm_bin):
            return ToolExecutionResult(
                success=False,
                output=f"FATALNA GREŠKA: nlm binarni fajl nije pronađen na {self.nlm_bin}.",
                error_type="binary_not_found",
                is_error=True,
            )

        cmd = [self.nlm_bin, "notebook", "query", notebook_id, query]
        env = self._get_nlm_env()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            raw_out = stdout.decode("utf-8", errors="replace").strip()
            raw_err = stderr.decode("utf-8", errors="replace").strip()

            if proc.returncode == 0 and raw_out:
                clean_lines = []
                for line in raw_out.splitlines():
                    if line.startswith("📊") or line.startswith("🔔 Update"):
                        continue
                    clean_lines.append(line)
                clean_output = "\n".join(clean_lines).strip()

                if not clean_output:
                    return ToolExecutionResult(
                        success=False,
                        output=f"GREŠKA: Google NotebookLM ({notebook_id}) je vratio prazan odgovor.",
                        error_type="empty_response",
                        is_error=True,
                    )

                return ToolExecutionResult(
                    success=True,
                    output=clean_output,
                    metadata={"notebook_id": notebook_id, "query": query},
                )
            else:
                err_msg = (
                    raw_err or raw_out or f"NLM returned exit code {proc.returncode}"
                )
                logger.error(
                    f"NotebookLM ({notebook_id}) upit nije uspeo: {err_msg}"
                )
                return ToolExecutionResult(
                    success=False,
                    output=f"GREŠKA: Nije moguće dohvatiti NotebookLM ({notebook_id}): {err_msg}",
                    error_type="nlm_fetch_failed",
                    is_error=True,
                )

        except asyncio.TimeoutError:
            logger.error(f"NotebookLM ({notebook_id}) timeout nakon {timeout}s")
            return ToolExecutionResult(
                success=False,
                output=f"GREŠKA: NotebookLM ({notebook_id}) poziv je prekinut zbog timeout-a ({timeout}s).",
                error_type="timeout",
                is_error=True,
            )
        except Exception as exc:
            logger.exception("Sistemska greška pri komunikaciji sa NotebookLM")
            return ToolExecutionResult(
                success=False,
                output=f"GREŠKA: Izuzetak pri pozivu NotebookLM: {exc}",
                error_type="system_exception",
                is_error=True,
            )

    async def execute_sandboxed_shell(
        self, command: str, reason: str = "Automated Tool Action"
    ) -> ToolExecutionResult:
        """Executes system command only after JudgeGuard Quorum PASS."""
        try:
            from judge_guard import JudgeGuard

            judge = JudgeGuard()
            verdict = judge.verify(command)
            if verdict != "PASSED":
                return ToolExecutionResult(
                    success=False,
                    output=f"JudgeGuard BLOKADA: Komanda '{command}' je blokirana.",
                    error_type="security_blocked",
                    is_error=True,
                )

            allowed_prefixes = (
                "systemctl --user status",
                "journalctl --user",
                "uptime",
                "free -h",
                "df -h",
                "git status",
                "git log",
                "nlm",
            )
            if not any(command.strip().startswith(p) for p in allowed_prefixes):
                return ToolExecutionResult(
                    success=False,
                    output=f"GREŠKA: Komanda '{command}' nije na listi dozvoljenih operacija.",
                    error_type="whitelist_violation",
                    is_error=True,
                )

            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=30.0
            )
            out_str = stdout.decode("utf-8", errors="replace").strip()
            err_str = stderr.decode("utf-8", errors="replace").strip()

            judge.log_complete(f"Shell execution: {command[:50]}")

            return ToolExecutionResult(
                success=(proc.returncode == 0),
                output=out_str if proc.returncode == 0 else (err_str or out_str),
                error_type=None if proc.returncode == 0 else "command_failed",
                is_error=(proc.returncode != 0),
            )
        except Exception as exc:
            return ToolExecutionResult(
                success=False,
                output=f"GREŠKA: Greška pri izvršavanju komande: {exc}",
                error_type="execution_exception",
                is_error=True,
            )


tools_runtime = A2ToolsRuntime()
