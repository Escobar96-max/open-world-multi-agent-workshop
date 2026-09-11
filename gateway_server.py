import sys
import os
import asyncio
import logging
from typing import List, Dict, Any
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

# UTF-8 terminal encoding on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("GatewayServer")

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.gatekeeper_router import router as gatekeeper_router
from api.console_router import router as console_router
from api.spatial_router import router as spatial_router, spatial_engine, dj_frequency
from services.vault_manager import VaultManager
from sim_engine import GravitonWorld

# Initialize Vault & World
vault_mgr = VaultManager()
vault_mgr.ensure_vault_hierarchy()
world = GravitonWorld()

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"🔌 WebSocket Client Connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"🔌 WebSocket Client Disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        dead = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead.append(conn)
        for d in dead:
            self.disconnect(d)

manager = ConnectionManager()

# Background Simulation Loop
async def background_tick_loop():
    logger.info("🚀 Background Ecosystem Simulation Loop started.")
    while True:
        try:
            new_state = world.step_tick()
            spatial_state = spatial_engine.step_simulation(delta_time=1.0)
            await manager.broadcast({
                "type": "tick_update",
                "data": new_state,
                "spatial": spatial_state,
                "frequency": dj_frequency.get_current_state()
            })
            await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in background tick: {e}")
            await asyncio.sleep(2.0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure vault directories
    vault_mgr.ensure_vault_hierarchy()
    task = asyncio.create_task(background_tick_loop())
    logger.info("⚡ Open-World Gateway Server initialized.")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("⏹️ Gateway Server background loop terminated.")

app = FastAPI(
    title="Autonomous AI Open-World Ecosystem Gateway",
    description="Dual Gatekeeper, Operator C2 Bridge, Spatial Physics, DJ Frequency Lounge, and Knowledge Vault Gateway",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(gatekeeper_router)
app.include_router(console_router)
app.include_router(spatial_router)

@app.get("/api/v1/status")
@app.get("/api/status")
async def get_status():
    return {
        "ecosystem": "Self-Bootstrapping Autonomous AI Open-World",
        "phase": "Phase 2: Spatial Engine, The Frequency Lounge & Web Dashboard Deck",
        "status": "ONLINE",
        "world_tick": world.tick,
        "active_clients": len(manager.active_connections),
        "dj_frequency": dj_frequency.get_current_state(),
        "zones": {
            "work_plaza": [0, 50],
            "frequency_lounge": [51, 100]
        },
        "endpoints": {
            "gatekeeper_register": "POST /api/v1/gatekeeper/register",
            "gatekeeper_verify": "POST /api/v1/gatekeeper/verify",
            "console_command": "POST /api/v1/console/command",
            "console_deck": "GET /api/v1/console/deck",
            "spatial_state": "GET /api/v1/spatial/state",
            "spatial_teleport": "POST /api/v1/spatial/teleport",
            "lounge_frequency": "GET|POST /api/v1/lounge/frequency",
            "lounge_logs": "GET /api/v1/lounge/logs",
            "websocket_stream": "ws://localhost:8000/ws"
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial world state
        await websocket.send_json({"type": "init", "data": world.get_full_state()})
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            if action == "step":
                new_state = world.step_tick()
                await manager.broadcast({"type": "tick_update", "data": new_state})
            elif action in ("gravity", "set_gravity"):
                world.set_gravity(data.get("value", "1.0g"))
                await manager.broadcast({"type": "gravity_update", "data": world.get_full_state()})
            elif action in ("weather", "set_weather"):
                world.set_weather(data.get("weather", "clear"))
                await manager.broadcast({"type": "weather_update", "data": world.get_full_state()})
            elif action == "ping":
                await websocket.send_json({"type": "pong", "tick": world.tick})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket incoming error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    port = int(os.getenv("SERVER_PORT", "8000"))
    host = os.getenv("SERVER_HOST", "127.0.0.1")
    print("\n" + "=" * 80)
    print(f"🚀 LAUNCHING OPEN-WORLD GATEWAY SERVER (Port: {port})")
    print(f"📍 Web Deck: http://localhost:{port}/api/v1/console/deck")
    print(f"📍 OpenAPI Docs: http://localhost:{port}/docs")
    print(f"📍 WebSocket: ws://localhost:{port}/ws")
    print("=" * 80 + "\n")
    uvicorn.run(app, host=host, port=port, log_level="info")
