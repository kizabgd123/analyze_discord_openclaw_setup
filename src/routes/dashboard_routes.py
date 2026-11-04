"""
dashboard_routes.py — FastAPI API Routes for React Data Application.
===================================================================
Exposes REST and SSE streaming endpoints consumed by the React + Vite frontend.
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any

from src.controllers.dashboard_controller import DashboardController
from src.validators.dashboard_schemas import DashboardChatRequestSchema, RAGSearchRequestSchema

router = APIRouter(prefix="/api", tags=["dashboard"])
controller = DashboardController()


@router.get("/kpis")
async def get_kpis() -> Dict[str, Any]:
    """Returns overview KPI summary."""
    res = controller.get_kpis()
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error"))
    return res["data"]


@router.get("/debates")
async def get_debates() -> Dict[str, Any]:
    """Returns multi-agent debate sessions, souls, and consensus charts."""
    res = controller.get_debates()
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error"))
    return res["data"]


@router.get("/rag")
async def get_rag() -> Dict[str, Any]:
    """Returns RAG database statistics and document list."""
    res = controller.get_rag()
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error"))
    return res["data"]


@router.post("/rag/search")
async def search_rag(payload: RAGSearchRequestSchema) -> Dict[str, Any]:
    """Searches indexed RAG documents."""
    res = controller.search_rag(payload.model_dump())
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@router.get("/research")
async def get_research() -> Dict[str, Any]:
    """Returns scientific study results and benchmark data."""
    res = controller.get_research()
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error"))
    return res["data"]


@router.get("/governance")
async def get_governance() -> Dict[str, Any]:
    """Returns task audit log and JudgeGuard metrics."""
    res = controller.get_governance()
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error"))
    return res["data"]


@router.get("/models")
async def get_models() -> Dict[str, Any]:
    """Returns LiteRT and local model execution status."""
    res = controller.get_models()
    if not res.get("success"):
        raise HTTPException(status_code=500, detail=res.get("error"))
    return res["data"]


@router.post("/chat")
async def chat_stream(payload: DashboardChatRequestSchema):
    """
    Server-Sent Events (SSE) streaming chat endpoint.
    Emits THOUGHT, CONTENT, SUGGESTION, and DONE events.
    """
    generator = controller.stream_chat(payload.model_dump())
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
