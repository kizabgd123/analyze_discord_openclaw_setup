#!/usr/bin/env python3
"""
BrainCore — Unified Cognitive Engine for OpenClaw / Antigravity 2.0
====================================================================
Implements the kognitivni šablon:

    brain = BrainCore(api_keys=..., database_path="antigravity_rag.db")
    knowledge = brain.retrieve_context(task, strategy="hybrid_rag")
    action    = brain.reason(knowledge, task)
    result    = brain.execute(action)  # Only called AFTER JudgeGuard passes

Architecture:
  - Tier 1: Local SQLite FTS5 full-text search (instant, offline)
  - Tier 2: Google NotebookLM via `nlm` CLI (authoritative, grounded)
  - VSR Funnel: Validate → Synthesize → Respond
  - Halt system on any unrecoverable error
"""

import os
import asyncio
import json
import logging
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BrainCore")

# ── Defaults ─────────────────────────────────────────────────────────────────
_NLM_BIN       = shutil.which("nlm") or "/home/kizamladjanijebac/.local/bin/nlm"
_DEFAULT_DB    = Path(__file__).parent / "antigravity_rag.db"
_SOUL_FILE     = Path(__file__).parent / "SOUL.md"
_MEMORY_FILE   = Path(__file__).parent / "MEMORY.md"
_NLM_TIMEOUT   = 120.0


# ── SQLite FTS5 helpers ──────────────────────────────────────────────────────

def _init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize (or open) the local RAG SQLite database with FTS5."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS rag_docs USING fts5(
            id UNINDEXED,
            source,
            title,
            body,
            created_at UNINDEXED,
            tokenize='porter unicode61'
        );
        CREATE TABLE IF NOT EXISTS rag_meta (
            id         TEXT PRIMARY KEY,
            source     TEXT,
            title      TEXT,
            body       TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS exec_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT,
            task        TEXT,
            action      TEXT,
            verdict     TEXT,
            result      TEXT
        );
    """)
    conn.commit()
    return conn


class BrainCore:
    """
    Main cognitive engine.  Use from async contexts (discord_bot.py) via
    the async_* wrappers; use sync methods in scripts/tests.

    Quick start:
        brain = BrainCore()
        ctx   = await brain.async_retrieve_context("What is JudgeGuard?")
        action = brain.reason(ctx, "What is JudgeGuard?")
        result = await brain.async_execute(action)
    """

    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        database_path: Optional[Path] = None,
        nlm_bin: str = _NLM_BIN,
        default_notebook_id: Optional[str] = None,
    ):
        self.api_keys            = api_keys or []
        self.db_path             = Path(database_path or _DEFAULT_DB)
        self.nlm_bin             = nlm_bin
        self.default_notebook_id = (
            default_notebook_id
            or os.getenv("NLM_NOTEBOOK_ID", "bf77f7c8-ae62-4eac-b6e5-a17ed6252676")
        )
        self._conn               = _init_db(self.db_path)
        self._soul               = self._load_file(_SOUL_FILE)
        self._memory             = self._load_file(_MEMORY_FILE)
        logger.info(f"BrainCore initialised | db={self.db_path} | nlm={self.nlm_bin}")

    # ── Context retrieval ────────────────────────────────────────────────────

    def retrieve_context(
        self,
        task_context: str,
        strategy: str = "hybrid_rag",
        notebook_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sync wrapper — blocks the calling thread.
        Prefer async_retrieve_context() from async code.
        """
        return asyncio.get_event_loop().run_until_complete(
            self.async_retrieve_context(task_context, strategy, notebook_id)
        )

    async def async_retrieve_context(
        self,
        task_context: str,
        strategy: str = "hybrid_rag",
        notebook_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Tier-1: FTS5 local search (fast)
        Tier-2: NotebookLM query (authoritative)
        Returns a merged context dict.
        """
        nb_id = notebook_id or self.default_notebook_id
        result: Dict[str, Any] = {
            "task": task_context,
            "strategy": strategy,
            "local_hits": [],
            "nlm_answer": "",
            "nlm_references": [],
            "soul_context": self._soul[:500] if self._soul else "",
            "memory_context": self._memory[:800] if self._memory else "",
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

        # Tier-1: FTS5
        if strategy in ("hybrid_rag", "fts5_only"):
            result["local_hits"] = self._fts5_search(task_context, limit=5)

        # Tier-2: NotebookLM
        if strategy in ("hybrid_rag", "nlm_only"):
            nlm_result = await self._nlm_query(nb_id, task_context)
            if nlm_result.get("success"):
                result["nlm_answer"]     = nlm_result.get("answer", "")
                result["nlm_references"] = nlm_result.get("references", [])
            else:
                result["nlm_error"] = nlm_result.get("error", "NLM query failed")

        return result

    # ── Reasoning (VSR Funnel) ───────────────────────────────────────────────

    def reason(
        self,
        knowledge_context: Dict[str, Any],
        task_context: str,
    ) -> Dict[str, Any]:
        """
        VSR Funnel — Validate → Synthesize → Respond.
        Returns a proposed_action dict ready for JudgeGuard.verify().
        """
        # V — Validate: is the context sufficient?
        confidence = self._compute_confidence(knowledge_context)

        # S — Synthesize: build answer from best available knowledge
        synthesis = self._synthesize(knowledge_context)

        # R — Respond: package as structured action
        proposed_action = {
            "type": "respond",
            "task": task_context,
            "synthesis": synthesis,
            "confidence": confidence,
            "sources_used": len(knowledge_context.get("local_hits", []))
                          + len(knowledge_context.get("nlm_references", [])),
            "proposed_at": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"[VSR] Confidence={confidence:.2f} | "
            f"sources={proposed_action['sources_used']} | "
            f"task={task_context[:60]}"
        )
        return proposed_action

    # ── Execution ────────────────────────────────────────────────────────────

    async def async_execute(self, proposed_action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an action that has already passed JudgeGuard.
        Logs result to exec_log table.
        """
        action_type = proposed_action.get("type", "respond")
        ts = datetime.now(timezone.utc).isoformat()

        try:
            if action_type == "respond":
                result = {
                    "ok": True,
                    "output": proposed_action.get("synthesis", ""),
                    "confidence": proposed_action.get("confidence", 0.0),
                    "sources": proposed_action.get("sources_used", 0),
                }
            elif action_type == "shell":
                cmd = proposed_action.get("command", "")
                result = await self._run_shell(cmd)
            elif action_type == "nlm_note":
                nb_id   = proposed_action.get("notebook_id", self.default_notebook_id)
                content = proposed_action.get("content", "")
                title   = proposed_action.get("title", "Brain Note")
                result  = await self._nlm_add_note(nb_id, content, title)
            else:
                result = {"ok": False, "error": f"Unknown action type: {action_type!r}"}

        except Exception as exc:
            logger.exception("Execution error")
            result = {"ok": False, "error": str(exc)}

        # Persist to exec_log
        self._conn.execute(
            "INSERT INTO exec_log (ts, task, action, verdict, result) VALUES (?,?,?,?,?)",
            (
                ts,
                proposed_action.get("task", ""),
                json.dumps(proposed_action, default=str),
                "EXECUTED",
                json.dumps(result, default=str),
            ),
        )
        self._conn.commit()
        return result

    # Sync convenience shim
    def execute(self, proposed_action: Dict[str, Any]) -> Dict[str, Any]:
        return asyncio.get_event_loop().run_until_complete(
            self.async_execute(proposed_action)
        )

    def halt_system(self, reason: str = "Safety Blocked") -> Dict[str, Any]:
        """Called when JudgeGuard returns BLOCKED."""
        logger.warning(f"[HALT] System halted: {reason}")
        ts = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO exec_log (ts, task, action, verdict, result) VALUES (?,?,?,?,?)",
            (ts, "", "", "HALTED", json.dumps({"reason": reason})),
        )
        self._conn.commit()
        return {"ok": False, "halted": True, "reason": reason}

    # ── Local knowledge management ───────────────────────────────────────────

    def ingest(self, source: str, title: str, body: str, doc_id: Optional[str] = None) -> str:
        """Add a document to the local FTS5 index."""
        doc_id = doc_id or f"{source}:{int(time.time())}"
        ts = datetime.now(timezone.utc).isoformat()

        # Upsert into meta table
        self._conn.execute(
            "INSERT OR REPLACE INTO rag_meta (id, source, title, body, created_at) VALUES (?,?,?,?,?)",
            (doc_id, source, title, body, ts),
        )
        # Insert into FTS (delete old entry first to avoid duplicates)
        self._conn.execute("DELETE FROM rag_docs WHERE id=?", (doc_id,))
        self._conn.execute(
            "INSERT INTO rag_docs (id, source, title, body, created_at) VALUES (?,?,?,?,?)",
            (doc_id, source, title, body, ts),
        )
        self._conn.commit()
        logger.info(f"Ingested: {title!r} [{doc_id}]")
        return doc_id

    def get_exec_log(self, limit: int = 20) -> List[Dict]:
        cur = self._conn.execute(
            "SELECT ts, task, verdict, result FROM exec_log ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]

    # ── Private helpers ──────────────────────────────────────────────────────

    def _fts5_search(self, query: str, limit: int = 5) -> List[Dict]:
        try:
            cur = self._conn.execute(
                "SELECT id, source, title, snippet(rag_docs,3,'>>','<<','...',20) AS excerpt "
                "FROM rag_docs WHERE rag_docs MATCH ? ORDER BY rank LIMIT ?",
                (query, limit),
            )
            return [dict(row) for row in cur.fetchall()]
        except sqlite3.OperationalError:
            return []

    async def _nlm_query(
        self,
        notebook_id: str,
        question: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        env = self._get_auth_env()
        cmd = [self.nlm_bin, "query", "notebook", "--json"]
        if conversation_id:
            cmd.extend(["--conversation-id", conversation_id])
        cmd.extend([notebook_id, question])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=_NLM_TIMEOUT
            )
            raw = stdout.decode("utf-8", errors="replace").strip()
            if proc.returncode != 0:
                return {"success": False, "error": stderr.decode()[:300]}
            data = json.loads(raw)
            return {
                "success": True,
                "answer": data.get("answer", ""),
                "references": data.get("references", []),
                "conversation_id": data.get("conversation_id"),
            }
        except asyncio.TimeoutError:
            return {"success": False, "error": "NLM timeout"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def _nlm_add_note(self, notebook_id: str, content: str, title: str) -> Dict:
        env = self._get_auth_env()
        cmd = [self.nlm_bin, "note", "create", notebook_id,
               "--content", content, "--title", title]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE, env=env
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            if proc.returncode == 0:
                return {"ok": True, "output": stdout.decode().strip()}
            return {"ok": False, "error": stderr.decode().strip()}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    async def _run_shell(self, command: str) -> Dict:
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            output = (stdout or stderr).decode("utf-8", errors="replace")
            return {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "output": output[:2000],
            }
        except asyncio.TimeoutError:
            return {"ok": False, "error": "Shell command timed out"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def _compute_confidence(ctx: Dict[str, Any]) -> float:
        score = 0.0
        if ctx.get("nlm_answer"):
            score += 0.6
        local_hits = ctx.get("local_hits", [])
        score += min(len(local_hits) * 0.1, 0.3)
        if ctx.get("memory_context"):
            score += 0.1
        return round(min(score, 1.0), 3)

    @staticmethod
    def _synthesize(ctx: Dict[str, Any]) -> str:
        """
        Synthesizes knowledge context into a concise, punchy, street-smart yet
        100% technically grounded response (Vratiće se rode style, zero fluff).
        """
        nlm_ans = (ctx.get("nlm_answer") or "").strip()
        local_hits = ctx.get("local_hits", [])

        # If we have real NLM answer, keep it clean and remove repetitive boilerplates
        if nlm_ans:
            # Clean up excessively long quotes or redundant footer boilerplates
            lines = [l for l in nlm_ans.splitlines() if not l.startswith("📊 Would you like me to generate")]
            cleaned = "\n".join(lines).strip()
            return cleaned

        # Fallback to local FTS5 hits if NLM wasn't available
        if local_hits:
            bullets = []
            for hit in local_hits[:3]:
                bullets.append(f"• **{hit.get('title','Dokument')}**: {hit.get('excerpt','').strip()}")
            return "Evo šta imamo direktno u lokalnoj bazi znanja:\n\n" + "\n".join(bullets)

        if ctx.get("memory_context"):
            mem = ctx["memory_context"].strip()
            return f"Iz lokalne memorije bota:\n{mem[:350]}..."

        return "Nema pronađenih podataka u sveskama za ovaj upit."

    @staticmethod
    def _get_auth_env() -> Dict[str, str]:
        env = os.environ.copy()
        nlm_env = Path.home() / ".nlm" / "env"
        if nlm_env.exists():
            try:
                for line in nlm_env.read_text().splitlines():
                    line = line.strip().lstrip("export ")
                    if "=" in line:
                        k, v = line.split("=", 1)
                        env[k] = v.strip("\"'")
            except Exception:
                pass
        return env

    @staticmethod
    def _load_file(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""
