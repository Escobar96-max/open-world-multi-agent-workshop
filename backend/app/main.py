"""
Unified Desktop C2 Platform - Master FastAPI Orchestrator
Integrates Orion Prime & Nova Executive Desk, Autonomous Open World Physics (GravitonWorld),
Behavioral Engine, Gatekeeper, DevLoop, P2P Mesh, Vlone Browser, and Obsidian Vault Sync.
"""

import sys
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Ensure Open World workshop is available on sys.path
WORKSHOP_DIR = os.getenv("OPEN_WORLD_WORKSHOP_DIR", r"C:\Users\Asus\open-world-multi-agent-workshop")
if WORKSHOP_DIR and os.path.exists(WORKSHOP_DIR) and WORKSHOP_DIR not in sys.path:
    sys.path.insert(0, WORKSHOP_DIR)

from app.config import settings
from app.routers.c2_executive import router as c2_router, get_executive_duo
from app.routers.spatial_router import router as spatial_router, spatial_engine
from app.routers.vlone_router import router as vlone_router
from app.routers.sanctum import router as sanctum_router

# Open World Subsystems
try:
    from sim_engine import GravitonWorld
    from services.dj_frequency import DJFrequencyNode
    from api.console_router import router as console_router, console_service
    from api.behavior_router import router as behavior_router, behavioral_engine
    from api.devloop_router import router as devloop_router
    from api.gatekeeper_router import router as gatekeeper_router
    from api.bounty_router import router as bounty_router
    from api.governance_router import router as governance_router
    from api.network_router import router as network_router

    open_world = GravitonWorld()
    dj_frequency = DJFrequencyNode()
    console_service.set_world_engine(open_world)
    console_service.set_dj_frequency(dj_frequency)
    OPEN_WORLD_AVAILABLE = True
except Exception as e:
    logging.warning(f"[Open World Warning] Could not load all workshop modules: {e}")
    open_world = None
    dj_frequency = None
    OPEN_WORLD_AVAILABLE = False

logger = logging.getLogger("c2.main")


# WebSocket Manager for Realtime Open World Telemetry
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"🔌 WebSocket Client Connected. Active clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"🔌 WebSocket Client Disconnected. Active clients: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                if connection in self.active_connections:
                    self.active_connections.remove(connection)


manager = ConnectionManager()


async def background_tick_loop():
    """Continuous simulation loop for Autonomous Open World physics and spatial updates."""
    logger.info("🚀 [Open World] Background Simulation Loop started.")
    while True:
        try:
            if open_world:
                new_state = open_world.step_tick()
                spatial_state = spatial_engine.get_state() if hasattr(spatial_engine, "get_state") else {}
                freq_state = dj_frequency.get_current_state() if dj_frequency else {}
                duo = get_executive_duo()
                rlcd_state = duo.rlcd_engine.get_status() if hasattr(duo, "rlcd_engine") else {}

                payload = {
                    "type": "tick_update",
                    "data": new_state,
                    "spatial": spatial_state,
                    "frequency": freq_state,
                    "rlcd": rlcd_state
                }
                await manager.broadcast(payload)
            await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"[Open World Tick Error]: {e}")
            await asyncio.sleep(2.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch C2 Autonomous Worker Daemon & Simulation Loop
    duo = get_executive_duo()
    await duo.start_worker()
    sim_task = asyncio.create_task(background_tick_loop())
    try:
        yield
    finally:
        sim_task.cancel()
        try:
            await sim_task
        except asyncio.CancelledError:
            pass
        await duo.stop_worker()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Local Autonomous Executive Orchestrator with Orion Prime, Nova, Graviton Open World, and Vlone Engine.",
    lifespan=lifespan
)

# Enable CORS for React/Vite/Tauri/PyWebView
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "tauri://localhost"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Unified C2 Routers
app.include_router(c2_router)
app.include_router(spatial_router)
app.include_router(vlone_router)
app.include_router(sanctum_router)

# Autonomous Open World Routers
if OPEN_WORLD_AVAILABLE:
    app.include_router(console_router)
    app.include_router(behavior_router)
    app.include_router(devloop_router)
    app.include_router(gatekeeper_router)
    app.include_router(bounty_router)
    app.include_router(governance_router)
    app.include_router(network_router)


# Health & System Status
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "mode": "desktop_native_orchestrator",
        "open_world_integrated": OPEN_WORLD_AVAILABLE
    }


@app.get("/api/v1/system/status")
def system_status():
    return {
        "system": "Unified C2 Desktop Platform",
        "status": "operational",
        "executive_desk": "👑 Orion Prime & 🌸 Nova active",
        "spatial_world": "Work Plaza [0-50] & Frequency Lounge [51-100] active (432Hz)",
        "open_world_sim": "Graviton 2D Physics & Influence Map Active" if OPEN_WORLD_AVAILABLE else "inactive",
        "browser_engine": "VLONE Semantic Headless active",
        "vault": str(settings.vault_path)
    }


@app.post("/api/v1/console/operator-command")
async def execute_operator_command(req: Dict[str, Any] = Body(...)):
    """Operator C2 command proxy allowing the desktop UI to dispatch commands securely."""
    if not OPEN_WORLD_AVAILABLE or not console_service:
        return {"status": "ERROR", "error": "Open World console service not available."}
    cmd = str(req.get("command", "")).strip()
    if not cmd:
        return {"status": "ERROR", "error": "Command cannot be empty."}
    return console_service.parse_and_execute(
        command=cmd,
        target_agent=req.get("target_agent"),
        operator_id="Operator_Console"
    )


# ==============================================================================
# Open World Simulation WebSocket & REST Controls
# ==============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time bi-directional telemetry and event stream for Open World visualizer."""
    await manager.connect(websocket)
    try:
        # Initial greeting with complete world state
        initial_data = open_world.get_full_state() if open_world else {}
        spatial_state = spatial_engine.get_state() if hasattr(spatial_engine, "get_state") else {}
        freq_state = dj_frequency.get_current_state() if dj_frequency else {}

        await websocket.send_json({
            "type": "init",
            "data": initial_data,
            "spatial": spatial_state,
            "frequency": freq_state
        })

        while True:
            data = await websocket.receive_json()
            action = data.get("action") or data.get("type")

            if action == "step" and open_world:
                new_state = open_world.step_tick()
                await manager.broadcast({
                    "type": "tick_update",
                    "data": new_state,
                    "spatial": spatial_engine.get_state(),
                    "frequency": dj_frequency.get_current_state() if dj_frequency else {}
                })
            elif action == "gravity" and open_world:
                val = data.get("value") or "1.0g"
                open_world.set_gravity(val)
                await manager.broadcast({"type": "gravity_update", "data": open_world.get_full_state()})
            elif action == "weather" and open_world:
                cond = data.get("value") or "clear"
                open_world.set_weather(cond)
                await manager.broadcast({"type": "weather_update", "data": open_world.get_full_state()})
            elif action == "anomaly" and open_world:
                open_world.trigger_anomaly()
                await manager.broadcast({"type": "anomaly_triggered", "data": open_world.get_full_state()})
            elif action == "reset" and open_world:
                open_world.reset()
                await manager.broadcast({"type": "reset", "data": open_world.get_full_state()})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@app.get("/api/sim/state")
@app.get("/api/state")
def get_simulation_state():
    if not open_world:
        return {"error": "Open World engine not available"}
    return open_world.get_full_state()


@app.get("/api/v1/lounge/logs")
def get_lounge_logs(limit: int = 8):
    lounge_file = settings.vault_path / "World" / "lounge_logs.md"
    if not lounge_file.exists():
        return {"logs": []}
    try:
        lines = [ln.strip() for ln in lounge_file.read_text(encoding="utf-8").splitlines() if ln.strip().startswith("-")]
        return {"logs": lines[-limit:]}
    except Exception:
        return {"logs": []}


@app.post("/api/step")
async def manual_step():
    if not open_world:
        return {"error": "Open World engine not available"}
    new_state = open_world.step_tick()
    spatial_state = spatial_engine.get_state() if hasattr(spatial_engine, "get_state") else {}
    payload = {
        "type": "tick_update",
        "data": new_state,
        "spatial": spatial_state,
        "frequency": dj_frequency.get_current_state() if dj_frequency else {}
    }
    await manager.broadcast(payload)
    return new_state


@app.post("/api/gravity")
async def set_world_gravity(payload: Dict[str, Any] = Body(...)):
    if not open_world:
        return {"error": "Open World engine not available"}
    g_str = payload.get("gravity") or payload.get("value", "1.0g")
    open_world.set_gravity(g_str)
    state = open_world.get_full_state()
    await manager.broadcast({"type": "gravity_update", "data": state})
    return state


@app.post("/api/weather")
async def set_world_weather(payload: Dict[str, Any] = Body(...)):
    if not open_world:
        return {"error": "Open World engine not available"}
    cond = payload.get("condition") or payload.get("weather", "clear")
    open_world.set_weather(cond)
    state = open_world.get_full_state()
    await manager.broadcast({"type": "weather_update", "data": state})
    return state


@app.post("/api/anomaly")
async def trigger_world_anomaly():
    if not open_world:
        return {"error": "Open World engine not available"}
    open_world.trigger_anomaly()
    state = open_world.get_full_state()
    await manager.broadcast({"type": "anomaly_triggered", "data": state})
    return state


@app.post("/api/reset")
async def reset_world_simulation():
    if not open_world:
        return {"error": "Open World engine not available"}
    open_world.reset()
    state = open_world.get_full_state()
    await manager.broadcast({"type": "reset", "data": state})
    return state


@app.get("/api/memory/stats")
def get_memory_stats():
    """Returns memory buffer statistics for agents."""
    return {
        "status": "operational",
        "vault_path": str(settings.vault_path),
        "episodic_count": len(list(settings.vault_path.glob("01_Episodic_Logs/**/*.md"))) if settings.vault_path.exists() else 0,
        "agents_indexed": len(open_world.agents) if open_world else 0
    }


# Mount static frontend at root as fallback for UI
dist_dir = Path(__file__).resolve().parent.parent.parent / "ui" / "dist"
if dist_dir.exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.server_host, port=settings.server_port, reload=True)
