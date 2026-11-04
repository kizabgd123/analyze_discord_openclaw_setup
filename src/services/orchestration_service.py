"""
orchestration_service.py — Multi-Agent Orchestration & ADK 2.0 Coordinator.
=============================================================================
Manages dynamic team formation, NotebookLM grounding, and task delegation.
Framework-agnostic domain service.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from src.config.unified_config import config
from src.services.nlm_service import NotebookLMService
from src.instrument import capture_exception, capture_message

logger = logging.getLogger("OrchestrationService")


class OrchestrationService:
    """Coordinates dynamic multi-agent execution pipeline."""

    def __init__(self, nlm_service: Optional[NotebookLMService] = None):
        self.nlm_service = nlm_service or NotebookLMService()

    async def execute_task(
        self,
        task: str,
        on_event_callback: Optional[Callable[[str, str], Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes the ADK dynamic role engine:
        1. Grounding via NotebookLM
        2. Dynamic role organization via Miki Nosonja
        3. Parallel execution of worker agents
        4. Final synthesis
        """
        logger.info(f"[OrchestrationService] Initiating ADK pipeline for task: {task[:60]}...")
        capture_message(f"Starting ADK execution for task: {task[:60]}", level="info")

        try:
            # Lazy import to prevent circular dependencies
            from adk_orchestration import adk_manager
            
            result = await adk_manager.execute_orchestration(
                user_task=task,
                on_event_callback=on_event_callback
            )
            return {"ok": True, "result": result}
        except Exception as exc:
            capture_exception(exc, {"task": task})
            if on_event_callback:
                await on_event_callback("System Error", f"Orkestracija nije uspela: {exc}")
            return {"ok": False, "error": str(exc)}
