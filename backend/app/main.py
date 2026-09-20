"""
Unified Desktop C2 Platform - Master FastAPI Orchestrator
Serves Orion Prime & Nova Executive Desk, Antigravity 2D Spatial Plane,
Vlone Headless Browser, and Obsidian Vault Sync.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.c2_executive import router as c2_router
from app.routers.spatial_router import router as spatial_router
from app.routers.vlone_router import router as vlone_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local Autonomous Executive Orchestrator with Orion Prime, Nova, Spatial World, and Vlone Engine."
)

# Enable CORS for React/Vite/Tauri/PyWebView
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from pathlib import Path

app.include_router(c2_router)
app.include_router(spatial_router)
app.include_router(vlone_router)

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "mode": "desktop_native_orchestrator"
    }


@app.get("/api/v1/system/status")
def system_status():
    return {
        "system": "Unified C2 Desktop Platform",
        "status": "operational",
        "executive_desk": "👑 Orion Prime & 🌸 Nova active",
        "spatial_world": "Work Plaza [0-50] & Frequency Lounge [51-100] active (432Hz)",
        "browser_engine": "VLONE Semantic Headless active",
        "vault": str(settings.vault_path)
    }


# Mount static frontend at root as fallback for UI
dist_dir = Path(__file__).resolve().parent.parent.parent / "ui" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.server_host, port=settings.server_port, reload=True)

