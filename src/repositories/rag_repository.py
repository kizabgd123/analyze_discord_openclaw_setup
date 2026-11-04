"""
rag_repository.py — Data Access Layer for SQLite FTS5 Local RAG.
================================================================
Encapsulates all database queries and indexing operations.
Direct database access in controllers or routes is strictly forbidden.
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from src.config.unified_config import config
from src.instrument import capture_exception

logger = logging.getLogger("RAGRepository")


class RAGRepository:
    """Repository handling SQLite FTS5 persistence for local document embeddings and texts."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.db.rag_db_path
        self._ensure_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self) -> None:
        """Create virtual table and metadata table if not present."""
        try:
            with self._get_connection() as conn:
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
                """)
        except Exception as exc:
            capture_exception(exc, {"db_path": str(self.db_path), "action": "ensure_tables"})
            raise

    def search_fts(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Executes full-text BM25 search over indexed documents."""
        # Sanitize query for FTS5 syntax
        clean_query = "".join(c for c in query if c.isalnum() or c in (" ", "_", "-")).strip()
        if not clean_query:
            return []

        fts_query = " OR ".join(f'"{token}"' for token in clean_query.split())

        try:
            with self._get_connection() as conn:
                cur = conn.execute(
                    """
                    SELECT id, source, title, body, created_at, rank
                    FROM rag_docs
                    WHERE rag_docs MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (fts_query, limit),
                )
                rows = cur.fetchall()
                return [dict(r) for r in rows]
        except Exception as exc:
            capture_exception(exc, {"query": query, "clean_query": clean_query})
            return []

    def insert_document(self, doc_id: str, source: str, title: str, body: str) -> bool:
        """Indexes a document into SQLite FTS5."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO rag_meta(id, source, title, body, created_at)
                    VALUES(?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        source=excluded.source,
                        title=excluded.title,
                        body=excluded.body,
                        created_at=excluded.created_at
                    """,
                    (doc_id, source, title, body, now),
                )
                conn.execute(
                    """
                    INSERT INTO rag_docs(id, source, title, body, created_at)
                    VALUES(?, ?, ?, ?, ?)
                    """,
                    (doc_id, source, title, body, now),
                )
                conn.commit()
            return True
        except Exception as exc:
            capture_exception(exc, {"doc_id": doc_id, "title": title})
            return False

    def count_documents(self) -> int:
        """Returns total indexed documents count."""
        try:
            with self._get_connection() as conn:
                cur = conn.execute("SELECT count(*) FROM rag_meta")
                row = cur.fetchone()
                return int(row[0]) if row else 0
        except Exception as exc:
            capture_exception(exc)
            return 0
