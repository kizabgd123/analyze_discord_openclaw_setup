"""
state_repository.py — Data Access Layer for System State & Configuration.
========================================================================
Manages atomic reads and writes to openclaw.json, debate_state.json, and MEMORY.md.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from src.config.unified_config import config
from src.instrument import capture_exception

logger = logging.getLogger("StateRepository")


class StateRepository:
    """Repository handling file-backed state stores and immutable logs."""

    def __init__(
        self,
        openclaw_path: Optional[Path] = None,
        debate_state_path: Optional[Path] = None,
        memory_path: Optional[Path] = None,
        work_log_path: Optional[Path] = None,
    ):
        self.openclaw_path = openclaw_path or config.db.openclaw_json_path
        self.debate_state_path = debate_state_path or config.db.debate_state_path
        self.memory_path = memory_path or config.db.memory_file
        self.work_log_path = work_log_path or config.db.work_log_path

    def load_openclaw_config(self) -> Dict[str, Any]:
        """Loads and parses the openclaw.json source of truth."""
        if not self.openclaw_path.exists():
            return {}
        try:
            with open(self.openclaw_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            capture_exception(exc, {"path": str(self.openclaw_path)})
            return {}

    def load_debate_state(self) -> Dict[str, Any]:
        """Loads the current debate session state."""
        if not self.debate_state_path.exists():
            return {}
        try:
            with open(self.debate_state_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return json.loads(content) if content else {}
        except Exception as exc:
            capture_exception(exc, {"path": str(self.debate_state_path)})
            return {}

    def save_debate_state(self, state: Dict[str, Any]) -> bool:
        """Atomically persists debate state to JSON."""
        try:
            temp_path = self.debate_state_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            temp_path.replace(self.debate_state_path)
            return True
        except Exception as exc:
            capture_exception(exc, {"path": str(self.debate_state_path)})
            return False

    def append_memory(self, content: str) -> bool:
        """Appends a timestamped cognitive record to MEMORY.md."""
        try:
            with open(self.memory_path, "a", encoding="utf-8") as f:
                f.write(f"\n{content.strip()}\n")
            return True
        except Exception as exc:
            capture_exception(exc, {"path": str(self.memory_path)})
            return False

    def append_work_log(self, entry: str) -> bool:
        """Appends an entry to WORK_LOG.md and touches mtime."""
        try:
            with open(self.work_log_path, "a", encoding="utf-8") as f:
                f.write(f"{entry.strip()}\n")
            return True
        except Exception as exc:
            capture_exception(exc, {"path": str(self.work_log_path)})
            return False
