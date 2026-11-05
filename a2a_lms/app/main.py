"""FastAPI Server with Real-time SSE Streaming (Google ADK A2A LMS).
Exposes /api/generate_course, /api/chat_stream, and /api/checkpoints endpoints.
Implements durable execution checkpointing and cost guards from autonomous-agents skill.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional, AsyncGenerator, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from a2a_lms.shared.schemas import CoursePayload
from a2a_lms.shared.checkpoint import LMSCheckpointManager
from a2a_lms.agents.orchestrator.agent import LMSOrchestrator

app = FastAPI(
    title="Google ADK A2A Multi-Agent LMS",
    description="Autonomous Agent-to-Agent Course Generation Engine grounded in NotebookLM 9c8878e1-1fb4-4035-b022-7678a10be7f3",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent / "frontend"
checkpoint_mgr = LMSCheckpointManager()


class CourseRequest(BaseModel):
    topic: str = Field(..., min_length=2, description="Course topic to research and generate")
    notebook_id: Optional[str] = Field("9c8878e1-1fb4-4035-b022-7678a10be7f3", description="NotebookLM brain ID")
    thread_id: Optional[str] = Field(None, description="Optional durable thread ID to resume or assign")
    resume: bool = Field(default=False, description="Whether to resume from existing checkpoint if available")


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "engine": "google-adk-2.0-a2a",
        "autonomous_guards": True,
        "zero_mock_enforced": True,
        "notebook_brain_id": "9c8878e1-1fb4-4035-b022-7678a10be7f3",
    }


@app.get("/api/checkpoints")
async def list_checkpoints():
    """Returns metadata for all persisted agent checkpoints."""
    return {"checkpoints": checkpoint_mgr.list_checkpoints()}


@app.get("/api/checkpoints/{thread_id}")
async def get_checkpoint(thread_id: str):
    """Retrieves full checkpoint state for a specific thread."""
    ckpt = checkpoint_mgr.load_checkpoint(thread_id)
    if not ckpt:
        raise HTTPException(status_code=404, detail=f"Checkpoint '{thread_id}' not found.")
    return ckpt


@app.post("/api/generate_course", response_model=CoursePayload)
async def generate_course(req: CourseRequest):
    """Direct execution endpoint for course generation with optional checkpoint resume."""
    try:
        orchestrator = LMSOrchestrator(notebook_id=req.notebook_id or "9c8878e1-1fb4-4035-b022-7678a10be7f3")
        course = await orchestrator.run(
            topic=req.topic,
            thread_id=req.thread_id,
            resume_from_checkpoint=req.resume,
        )
        return course
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"A2A Multi-Agent Engine error: {str(e)}")


@app.get("/api/chat_stream")
async def chat_stream(
    topic: str = Query(..., min_length=2, description="Topic for course generation"),
    notebook_id: str = Query("9c8878e1-1fb4-4035-b022-7678a10be7f3", description="NotebookLM brain ID"),
    thread_id: Optional[str] = Query(None, description="Optional thread ID"),
    resume: bool = Query(False, description="Resume from checkpoint"),
):
    """Server-Sent Events (SSE) streaming endpoint providing live agent status."""
    async def event_generator() -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue()

        def progress_callback(msg: str):
            queue.put_nowait({"type": "progress", "message": msg})

        async def worker():
            try:
                orchestrator = LMSOrchestrator(notebook_id=notebook_id)
                course = await orchestrator.run(
                    topic=topic,
                    thread_id=thread_id,
                    resume_from_checkpoint=resume,
                    on_progress=progress_callback,
                )
                await queue.put({"type": "complete", "data": course.model_dump()})
            except Exception as err:
                await queue.put({"type": "error", "message": str(err)})

        # Start worker in background
        task = asyncio.create_task(worker())

        while True:
            item = await queue.get()
            event_type = item.get("type")

            if event_type == "progress":
                yield f"event: progress\ndata: {json.dumps(item)}\n\n"
            elif event_type == "complete":
                yield f"event: complete\ndata: {json.dumps(item)}\n\n"
                break
            elif event_type == "error":
                yield f"event: error\ndata: {json.dumps(item)}\n\n"
                break

        await task

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Static file routes for LMS frontend
if FRONTEND_DIR.exists():
    @app.get("/", response_class=FileResponse)
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/course.html", response_class=FileResponse)
    async def serve_course_page():
        return FileResponse(FRONTEND_DIR / "course.html")

    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
