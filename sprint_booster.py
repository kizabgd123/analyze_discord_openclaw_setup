#!/usr/bin/env python3
"""
sprint_booster.py — Token Optimization, Context Compaction, and Store-by-Reference Pipeline.
===========================================================================================
- Saves full agent outputs to .cm/sprint/artifacts/{session_id}/
- Creates concise summaries (< 1500 characters) with path to artifact file
- Prunes incoming prompt payloads (removes redundancy and respects token budgets)
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("SprintBooster")

class SprintBooster:
    def __init__(self, session_id: str = "default_session", artifacts_base_dir: str = ".cm/sprint/artifacts"):
        self.session_id = session_id
        self.artifacts_dir = Path(artifacts_base_dir) / session_id
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def store_artifact(self, agent_name: str, content: str, extension: str = "md") -> str:
        """
        Skladišti pune izlaze agenata u .cm/sprint/artifacts/{session_id}/ i vraća apsolutnu putanju.
        """
        safe_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in agent_name)
        filename = f"{safe_name}_output.{extension}"
        file_path = self.artifacts_dir / filename
        
        try:
            file_path.write_text(content, encoding="utf-8")
            logger.info(f"[SprintBooster] Sačuvan artefakt za {agent_name} na {file_path.absolute()}")
            return str(file_path.absolute())
        except Exception as e:
            logger.error(f"[SprintBooster] Greška pri skladištenju artefakta za {agent_name}: {e}")
            return ""

    def summarize_output(self, agent_name: str, full_output: str, artifact_path: str, max_chars: int = 1000) -> str:
        """
        Kreira sažeti izvod (< 1500 karaktera) sa putanjom ka fajlu artefakta.
        """
        if len(full_output) <= max_chars:
            summary = full_output
        else:
            summary = full_output[:max_chars] + f"\n\n[...TRUNCATED_FOR_TOKEN_BUDGET... Full output stored in artifact...]"

        compressed_relay = (
            f"=== SPRINT BOOSTER COMPRESSED RELAY [{agent_name}] ===\n"
            f"Artifact Path: {artifact_path}\n"
            f"Length: {len(full_output)} chars\n\n"
            f"Summary / Key Findings:\n{summary}\n"
            f"=================================================="
        )
        return compressed_relay

    def prune_prompt(self, prompt_payload: str, max_length: int = 4000) -> str:
        """
        Prunuje ulazni prompt payload (uklanja redundansu i poštuje token budžet).
        """
        if not prompt_payload:
            return ""
        
        lines = prompt_payload.splitlines()
        cleaned_lines = []
        seen = set()
        for line in lines:
            stripped = line.strip()
            if stripped not in seen or not stripped:
                seen.add(stripped)
                cleaned_lines.append(line)
        
        pruned = "\n".join(cleaned_lines)
        if len(pruned) > max_length:
            pruned = pruned[:max_length] + "\n[...PRUNED_PAYLOAD_LIMIT_REACHED...]"
            
        return pruned
