"""
nlm_service.py — Domain Service for Google NotebookLM Operations.
================================================================
Encapsulates all Google NotebookLM business logic via the official unified `nlm` CLI.
Framework-agnostic: contains zero Discord dependencies.
"""

import os
import re
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from src.config.unified_config import config
from src.instrument import capture_exception, capture_message

logger = logging.getLogger("NotebookLMService")


class NotebookLMService:
    """Service orchestrating real Google NotebookLM knowledge retrieval and management."""

    def __init__(self, binary_path: Optional[str] = None):
        self.binary_path = binary_path or config.nlm.binary_path
        self._notebook_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = asyncio.Lock()

    def _get_auth_env(self) -> Dict[str, str]:
        """Loads and prepares Google auth tokens from ~/.nlm/env."""
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
            except Exception as exc:
                capture_exception(exc, {"path": nlm_env_file})
        return env

    async def check_health(self) -> Dict[str, Any]:
        """Validates connection health and CLI binary responsiveness."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self.binary_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            version = stdout.decode().strip()
            return {
                "ok": proc.returncode == 0,
                "version": version or "unknown",
                "binary": self.binary_path
            }
        except Exception as exc:
            capture_exception(exc, {"binary": self.binary_path})
            return {"ok": False, "error": str(exc), "binary": self.binary_path}

    async def list_notebooks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves user's Google NotebookLM notebooks."""
        async with self._cache_lock:
            try:
                proc = await asyncio.create_subprocess_exec(
                    self.binary_path, "list", "--json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=self._get_auth_env()
                )
                stdout, stderr = await proc.communicate()
                if proc.returncode != 0:
                    err_msg = stderr.decode().strip()
                    capture_message(f"NLM list failed: {err_msg}", level="warning")
                    return list(self._notebook_cache.values())

                raw = stdout.decode().strip()
                data = json.loads(raw)
                notebooks = data.get("notebooks", []) if isinstance(data, dict) else data

                result = []
                for nb in notebooks[:limit]:
                    nb_id = nb.get("id") or nb.get("notebook_id")
                    title = nb.get("title", "Neimenovana sveska")
                    entry = {"id": nb_id, "title": title}
                    self._notebook_cache[nb_id] = entry
                    result.append(entry)
                return result
            except Exception as exc:
                capture_exception(exc)
                return list(self._notebook_cache.values())

    async def query_notebook(self, query: str, notebook_id: Optional[str] = None) -> str:
        """Submits a question to Google NotebookLM and returns the grounded answer."""
        target_nb = notebook_id or config.nlm.default_notebook_id
        cmd = [self.binary_path, "query", "--notebook", target_nb, query]

        logger.info(f"[NLM Service] Querying notebook '{target_nb}': {query[:60]}...")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_auth_env()
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=config.nlm.timeout_seconds
            )

            if proc.returncode != 0:
                err = stderr.decode().strip()
                raise RuntimeError(f"NLM CLI query failed with code {proc.returncode}: {err}")

            response_text = stdout.decode().strip()
            # Clean possible CLI banner or ANSI escapes
            clean_text = re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", response_text)
            return clean_text or "(Odgovor iz sveske je prazan)"
        except asyncio.TimeoutError:
            err = TimeoutError(f"NLM CLI query timed out after {config.nlm.timeout_seconds}s")
            capture_exception(err, {"notebook_id": target_nb, "query": query})
            raise err
        except Exception as exc:
            capture_exception(exc, {"notebook_id": target_nb, "query": query})
            raise

    async def add_note(self, text: str, title: Optional[str] = None, notebook_id: Optional[str] = None) -> bool:
        """Adds a note directly to the target notebook."""
        target_nb = notebook_id or config.nlm.default_notebook_id
        cmd = [self.binary_path, "note", "--notebook", target_nb]
        if title:
            cmd.extend(["--title", title])
        cmd.append(text)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_auth_env()
            )
            stdout, stderr = await proc.communicate()
            return proc.returncode == 0
        except Exception as exc:
            capture_exception(exc, {"notebook_id": target_nb, "title": title})
            return False
