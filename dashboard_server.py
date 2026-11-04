"""
dashboard_server.py — FastAPI Application Entrypoint for Antigravity Data Portal.
=================================================================================
Runs FastAPI backend serving REST + SSE endpoints and hosting Vite production build.
"""

import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.routes.dashboard_routes import router as dashboard_router
from src.config.unified_config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("DashboardServer")

app = FastAPI(
    title="Antigravity Multi-Agent Data & Observability Portal",
    description="React + FastAPI dashboard for multi-agent debates, RAG, research benchmarks, and LiteRT runtime.",
    version="1.0.0",
)

# CORS Configuration for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Dashboard API routes
app.include_router(dashboard_router)


@app.get("/health")
async def health_check():
    """Health check endpoint for container / orchestrator probes."""
    return {"status": "healthy", "service": "antigravity-dashboard", "version": "1.0.0"}


# Mount static build files if frontend/dist exists
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("DASHBOARD_PORT", "8000"))
    host = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    logger.info(f"Pokrećem Antigravity Data Dashboard na http://{host}:{port}")
    uvicorn.run("dashboard_server:app", host=host, port=port, reload=False)
