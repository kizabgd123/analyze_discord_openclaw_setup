#!/usr/bin/env python3
"""
src/services/sprint_booster_service.py — Servisni adapter za SprintBooster.
==========================================================================
Pruža čistu interfejsnu klasu za integraciju Store-by-Reference i Token Pruning
mehanizama u ADK i orkestracijske pipeline-ove.
"""

import os
from typing import Optional
from sprint_booster import SprintBooster

class SprintBoosterService:
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or os.getenv("CM_SESSION_ID", "default_session")
        self.booster = SprintBooster(session_id=self.session_id)

    def process_agent_output(self, agent_name: str, full_output: str) -> str:
        """
        Skladišti pun izlaz kao artefakt i vraća sažeti preneseni izvod (< 1500 karaktera).
        """
        artifact_path = self.booster.store_artifact(agent_name, full_output)
        summary_relay = self.booster.summarize_output(agent_name, full_output, artifact_path)
        return summary_relay

    def optimize_prompt(self, payload: str, max_length: int = 4000) -> str:
        """
        Prunuje i optimizuje ulazni prompt payload.
        """
        return self.booster.prune_prompt(payload, max_length=max_length)
