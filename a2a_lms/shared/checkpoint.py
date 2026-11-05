"""Durable Execution & Checkpoint State Persistence for Autonomous Agents.
Enables server restart survival, crash recovery, and time-travel replay.
Based on LangGraph durable checkpointing pattern from autonomous-agents skill.
"""

import json
import os
import time
import uuid
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel

logger = logging.getLogger("a2a_lms.checkpoint")

DEFAULT_CHECKPOINT_DIR = Path(__file__).parent.parent / "checkpoints"


class LMSCheckpointManager:
    """Persists intermediate agent state to disk for fault-tolerant resumption."""

    def __init__(self, checkpoint_dir: Optional[Path] = None):
        self.checkpoint_dir = checkpoint_dir or DEFAULT_CHECKPOINT_DIR
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, thread_id: str) -> Path:
        # Sanitize thread_id to prevent path traversal
        safe_id = "".join(c for c in thread_id if c.isalnum() or c in ("-", "_"))
        return self.checkpoint_dir / f"{safe_id}.json"

    def create_thread_id(self, prefix: str = "lms") -> str:
        """Generates a unique durable session thread identifier."""
        return f"{prefix}-{uuid.uuid4().hex[:12]}"

    def save_checkpoint(
        self,
        thread_id: str,
        stage: str,
        topic: str,
        state_data: Dict[str, Any],
        iteration: int = 1,
    ) -> str:
        """Atomically saves checkpoint state to disk."""
        target_path = self._file_path(thread_id)
        tmp_path = target_path.with_suffix(".tmp")

        payload = {
            "thread_id": thread_id,
            "topic": topic,
            "current_stage": stage,
            "iteration": iteration,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "state": state_data,
        }

        # Convert any embedded Pydantic objects or non-serializable objects
        def json_encoder(obj):
            if isinstance(obj, BaseModel):
                return obj.model_dump()
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False, default=json_encoder)

        tmp_path.replace(target_path)
        logger.info(f"[Checkpoint] State saved for thread={thread_id} at stage='{stage}'")
        return str(target_path)

    def load_checkpoint(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Loads persistent state for thread_id if present."""
        target_path = self._file_path(thread_id)
        if not target_path.exists():
            logger.warning(f"[Checkpoint] Thread {thread_id} not found at {target_path}")
            return None

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[Checkpoint] Failed to read checkpoint {thread_id}: {e}")
            return None

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """Lists metadata of all stored agent checkpoints."""
        results = []
        for p in self.checkpoint_dir.glob("*.json"):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    results.append({
                        "thread_id": data.get("thread_id"),
                        "topic": data.get("topic"),
                        "current_stage": data.get("current_stage"),
                        "timestamp": data.get("timestamp"),
                        "iteration": data.get("iteration", 1),
                        "file_size": p.stat().st_size,
                    })
            except Exception:
                continue
        results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return results

    def delete_checkpoint(self, thread_id: str) -> bool:
        """Deletes checkpoint on cleanup."""
        target_path = self._file_path(thread_id)
        if target_path.exists():
            target_path.unlink()
            return True
        return False
