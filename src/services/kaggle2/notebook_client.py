"""
notebook_client.py — Google NotebookLM Integration Client for S6E11 Multi-Agent Competition.
=============================================================================================
Provides asynchronous querying, verbatim logging, and automatic source ingestion for NotebookLM.
Guarantees:
  - Available to EVERY agent in EVERY turn.
  - Verbatim error logging: if query fails, marked FAILED with raw stderr. Never invent answers.
  - Rate limiting & budget tracking.
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("Kaggle2.NotebookClient")

DEFAULT_S6E11_NOTEBOOK_ID = "1d5affac-14fc-49e2-99a3-90bdc36767db"


def classify_source_origin(url: Optional[str], title: str) -> str:
    """Classifies source origin into one of the required categories."""
    if not url:
        if title.lower().startswith("lesson") or "lesson_" in title.lower():
            return "lesson"
        return "local reference"
    
    url_lower = url.lower()
    if "/discussion/" in url_lower:
        return "discussion"
    elif "/code/" in url_lower:
        return "public notebook"
    elif "kaggle.com/competitions/" in url_lower:
        return "Kaggle page"
    elif "github.com" in url_lower:
        return "repo"
    elif any(domain in url_lower for domain in ["arxiv.org", "preprints.org", "ijhess.com", "thescipub.com", "researchsquare.com", "spectrumofresearch.com"]):
        return "academic"
    return "external reference"


class NotebookLMClient:
    """Async client wrapping the unified `nlm` CLI with strict failure handling."""

    def __init__(self, notebook_id: str = DEFAULT_S6E11_NOTEBOOK_ID, binary_path: str = "nlm"):
        self.notebook_id = notebook_id
        self.binary_path = binary_path
        self.query_count = 0
        self.max_queries_per_run = 100
        self._lock = asyncio.Lock()

    def _get_env(self) -> Dict[str, str]:
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
                logger.warning(f"Error reading ~/.nlm/env: {e}")
        return env

    async def query_notebook(self, question: str, timeout: float = 120.0) -> Dict[str, Any]:
        """
        Submits a question to Google NotebookLM.
        Returns dictionary with status ('PASSED' or 'FAILED'), verbatim answer, citations, and error.
        """
        async with self._lock:
            self.query_count += 1
            if self.query_count > self.max_queries_per_run:
                raw_err = f"NotebookLM query budget exceeded ({self.query_count} > {self.max_queries_per_run})"
                logger.error(raw_err)
                return {
                    "status": "FAILED",
                    "question": question,
                    "answer": None,
                    "citations": {},
                    "sources_used": [],
                    "error": raw_err,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        cmd = [self.binary_path, "query", "notebook", self.notebook_id, question, "--json"]
        logger.info(f"[NLM Query #{self.query_count}] {question[:75]}...")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_env()
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            raw_stdout = stdout.decode().strip()
            raw_stderr = stderr.decode().strip()

            if proc.returncode != 0:
                raw_err = raw_stderr or raw_stdout or f"Process exited with code {proc.returncode}"
                logger.warning(f"NLM Query failed: {raw_err}")
                return {
                    "status": "FAILED",
                    "question": question,
                    "answer": None,
                    "citations": {},
                    "sources_used": [],
                    "error": raw_err,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

            # Attempt parsing JSON response
            try:
                data = json.loads(raw_stdout)
                return {
                    "status": "PASSED",
                    "question": question,
                    "answer": data.get("answer", raw_stdout),
                    "citations": data.get("citations", {}),
                    "sources_used": data.get("sources_used", []),
                    "error": None,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            except json.JSONDecodeError:
                # CLI produced non-JSON text output
                return {
                    "status": "PASSED",
                    "question": question,
                    "answer": raw_stdout,
                    "citations": {},
                    "sources_used": [],
                    "error": None,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        except asyncio.TimeoutError:
            raw_err = f"NLM query timed out after {timeout} seconds"
            logger.error(raw_err)
            return {
                "status": "FAILED",
                "question": question,
                "answer": None,
                "citations": {},
                "sources_used": [],
                "error": raw_err,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as exc:
            raw_err = f"Exception executing NLM CLI: {type(exc).__name__}: {exc}"
            logger.error(raw_err)
            return {
                "status": "FAILED",
                "question": question,
                "answer": None,
                "citations": {},
                "sources_used": [],
                "error": raw_err,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def add_source_file(self, file_path: str, title: Optional[str] = None, timeout: float = 300.0) -> Dict[str, Any]:
        """Uploads a local file (e.g. structured lesson) to NotebookLM as a new source."""
        cmd = [self.binary_path, "source", "add", self.notebook_id, "--file", file_path, "--wait"]
        if title:
            cmd.extend(["--title", title])

        logger.info(f"[NLM Ingest] Ingesting source file {file_path} (title: {title})...")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_env()
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            raw_stdout = stdout.decode().strip()
            raw_stderr = stderr.decode().strip()

            if proc.returncode != 0:
                raw_err = raw_stderr or raw_stdout or f"Process exited with code {proc.returncode}"
                return {"status": "FAILED", "error": raw_err}

            return {"status": "PASSED", "output": raw_stdout}
        except Exception as exc:
            return {"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}

    async def list_sources(self, timeout: float = 60.0) -> List[Dict[str, Any]]:
        """Returns the full list of sources in the notebook with classified origins."""
        cmd = [self.binary_path, "source", "list", self.notebook_id, "--json"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_env()
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            if proc.returncode != 0:
                logger.error(f"Failed to list sources: {stderr.decode().strip()}")
                return []
            sources = json.loads(stdout.decode().strip())
            for s in sources:
                s["origin"] = classify_source_origin(s.get("url"), s.get("title", ""))
            return sources
        except Exception as exc:
            logger.error(f"Error listing sources: {exc}")
            return []
