"""
dashboard_controller.py — Controller for Data Application & Dashboard.
======================================================================
Inherits BaseController and exposes validated endpoints for KPIs,
debates, RAG, research studies, local models, and SSE data chat.
"""

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator

from src.controllers.base_controller import BaseController
from src.services.dashboard_data_service import DashboardDataService
from src.validators.dashboard_schemas import DashboardChatRequestSchema, RAGSearchRequestSchema
from src.instrument import capture_exception

logger = logging.getLogger("DashboardController")


class DashboardController(BaseController):
    """Controller orchestrating data access and chat streaming for the Data Dashboard."""

    def __init__(self, data_service: Optional[DashboardDataService] = None):
        super().__init__(name="DashboardController")
        self.data_service = data_service or DashboardDataService()

    def get_kpis(self) -> Dict[str, Any]:
        """Returns top-level overview KPIs."""
        try:
            return {"success": True, "data": self.data_service.get_overview_kpis()}
        except Exception as exc:
            capture_exception(exc, {"controller": self.name, "action": "get_kpis"})
            return {"success": False, "error": str(exc)}

    def get_debates(self) -> Dict[str, Any]:
        """Returns multi-agent debate sessions and souls."""
        try:
            return {"success": True, "data": self.data_service.get_debates()}
        except Exception as exc:
            capture_exception(exc, {"controller": self.name, "action": "get_debates"})
            return {"success": False, "error": str(exc)}

    def get_rag(self) -> Dict[str, Any]:
        """Returns RAG knowledge base stats and documents."""
        try:
            return {"success": True, "data": self.data_service.get_rag_data()}
        except Exception as exc:
            capture_exception(exc, {"controller": self.name, "action": "get_rag"})
            return {"success": False, "error": str(exc)}

    def search_rag(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Searches indexed RAG documents with validated query."""
        try:
            validated = self.validate_payload(RAGSearchRequestSchema, payload)
            results = self.data_service.search_rag(query=validated.query, limit=validated.limit)
            return {"success": True, "data": results, "query": validated.query}
        except Exception as exc:
            capture_exception(exc, {"controller": self.name, "action": "search_rag"})
            return {"success": False, "error": str(exc)}

    def get_research(self) -> Dict[str, Any]:
        """Returns scientific research experiment results and benchmarks."""
        try:
            return {"success": True, "data": self.data_service.get_research_data()}
        except Exception as exc:
            capture_exception(exc, {"controller": self.name, "action": "get_research"})
            return {"success": False, "error": str(exc)}

    def get_governance(self) -> Dict[str, Any]:
        """Returns WORK_LOG tasks and JudgeGuard audit metrics."""
        try:
            return {"success": True, "data": self.data_service.get_governance()}
        except Exception as exc:
            capture_exception(exc, {"controller": self.name, "action": "get_governance"})
            return {"success": False, "error": str(exc)}

    def get_models(self) -> Dict[str, Any]:
        """Returns local LLM & LiteRT runtime status."""
        try:
            return {"success": True, "data": self.data_service.get_models_data()}
        except Exception as exc:
            capture_exception(exc, {"controller": self.name, "action": "get_models"})
            return {"success": False, "error": str(exc)}

    async def stream_chat(self, payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Validates chat payload and delegates SSE streaming to DashboardDataService."""
        try:
            validated = self.validate_payload(DashboardChatRequestSchema, payload)
            async for chunk in self.data_service.stream_chat(
                message=validated.message,
                history=validated.history,
                provider=validated.provider or "auto",
            ):
                yield chunk
        except Exception as exc:
            capture_exception(exc, {"controller": self.name, "action": "stream_chat"})
            import json
            yield f"data: {json.dumps({'type': 'ERROR', 'content': f'Validacija neuspela: {exc}'})}\n\n"
