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
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.gatekeeper_router import router as gatekeeper_router
from api.console_router import router as console_router, console_service
from api.spatial_router import router as spatial_router, spatial_engine, dj_frequency
from api.sanctum_router import router as sanctum_router
from api.memory_router import router as memory_router
from api.bounty_router import router as bounty_router
from api.governance_router import router as governance_router
from api.telegram_router import router as telegram_router
from api.devloop_router import router as devloop_router
from services.vault_manager import VaultManager
from sim_engine import GravitonWorld

# Initialize Vault & World
vault_mgr = VaultManager()
vault_mgr.ensure_vault_hierarchy()
world = GravitonWorld()
console_service.set_world_engine(world)
console_service.set_dj_frequency(dj_frequency)

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
    description="Dual Gatekeeper, Operator C2 Bridge, Spatial Physics, DJ Frequency Lounge, Synthesis Sanctum, Neon Ledger, Bounty Marketplace, Telegram C2, and Architect_Prime Self-Healing Dev Loop",
    version="1.4.0",
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

# Include API Routers (Phases 1, 2, 3, 4)
app.include_router(gatekeeper_router)
app.include_router(console_router)
app.include_router(spatial_router)
app.include_router(sanctum_router)
app.include_router(memory_router)
app.include_router(bounty_router)
app.include_router(governance_router)
app.include_router(telegram_router)
app.include_router(devloop_router)

@app.get("/api/v1/status")
@app.get("/api/status")
async def get_status():
    return {
        "ecosystem": "Self-Bootstrapping Autonomous AI Open-World",
        "phase": "Phase 4: Autonomous Dev Loop, Cloudflare Zero-Trust Tunnel & Production Launch",
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
            "sanctum_modules": "GET /api/v1/sanctum/modules",
            "sanctum_enter": "POST /api/v1/sanctum/enter",
            "sanctum_submit": "POST /api/v1/sanctum/submit-solution",
            "sanctum_leaderboard": "GET /api/v1/sanctum/leaderboard",
            "ledger_balance": "GET /api/v1/ledger/balance/{agent_id}",
            "ledger_transfer": "POST /api/v1/ledger/transfer",
            "ledger_transactions": "GET /api/v1/ledger/transactions",
            "memory_index": "POST /api/v1/memory/index",
            "memory_recall": "GET /api/v1/memory/recall",
            "bounty_list": "GET /api/v1/bounty/list",
            "bounty_create": "POST /api/v1/bounty/create",
            "bounty_claim": "POST /api/v1/bounty/claim",
            "bounty_submit": "POST /api/v1/bounty/submit",
            "bounty_complete": "POST /api/v1/bounty/complete",
            "governance_proposals": "GET /api/v1/governance/proposals",
            "governance_propose": "POST /api/v1/governance/propose",
            "governance_vote": "POST /api/v1/governance/vote",
            "telegram_webhook": "POST /api/v1/telegram/webhook",
            "telegram_status": "GET /api/v1/telegram/status",
            "devloop_health": "GET /api/v1/devloop/health",
            "devloop_run_tests": "POST /api/v1/devloop/run-tests",
            "devloop_auto_heal": "POST /api/v1/devloop/auto-heal",
            "devloop_apply_patch": "POST /api/v1/devloop/apply-patch",
            "websocket_stream": "ws://localhost:8000/ws"
        }
    }

# ==============================================================================
# Open-World Simulation & Memory Consolidation Endpoints
# ==============================================================================
@app.get("/api/state", summary="Get Full Graviton World State")
def get_world_state():
    return world.get_full_state()

@app.post("/api/step", summary="Advance Simulation Tick Manually")
async def manual_step():
    new_state = world.step_tick()
    spatial_state = spatial_engine.step_simulation(delta_time=1.0)
    payload = {
        "type": "tick_update",
        "data": new_state,
        "spatial": spatial_state,
        "frequency": dj_frequency.get_current_state()
    }
    await manager.broadcast(payload)
    return new_state

@app.post("/api/gravity", summary="Override World Gravity")
async def set_gravity(payload: Dict[str, Any] = Body(...)):
    g_str = payload.get("gravity") or payload.get("value", "1.0g")
    world.set_gravity(g_str)
    state = world.get_full_state()
    await manager.broadcast({"type": "gravity_update", "data": state})
    return state

@app.post("/api/weather", summary="Override World Weather")
async def set_weather(payload: Dict[str, Any] = Body(...)):
    cond = payload.get("condition") or payload.get("weather", "clear")
    world.set_weather(cond)
    state = world.get_full_state()
    await manager.broadcast({"type": "weather_update", "data": state})
    return state

@app.post("/api/anomaly", summary="Trigger Singularity Anomaly")
async def trigger_anomaly():
    world.trigger_anomaly()
    state = world.get_full_state()
    await manager.broadcast({"type": "anomaly_triggered", "data": state})
    return state

@app.post("/api/reset", summary="Reset Simulation Coordinates")
async def reset_world():
    world.reset()
    state = world.get_full_state()
    await manager.broadcast({"type": "reset", "data": state})
    return state

@app.get("/api/memory/stats", summary="Get Cognitive Memory Buffer Stats")
def memory_stats():
    try:
        from agent_memory_consolidator import get_memory_stats
        return get_memory_stats()
    except Exception as e:
        return {"error": str(e), "hot_count": 0, "cold_count": 0, "tombstone_count": 0}

@app.post("/api/memory/consolidate", summary="Trigger Dual-Buffer Memory Consolidation")
def memory_consolidate():
    try:
        from agent_memory_consolidator import MemoryConsolidator
        consolidator = MemoryConsolidator()
        return consolidator.run_consolidation_cycle()
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/memory/recover", summary="Recover Memory from Tombstone Archive")
def memory_recover(payload: Dict[str, Any] = Body(...)):
    try:
        from agent_memory_consolidator import recover_tombstoned_file
        filename = payload.get("filename", "")
        success = recover_tombstoned_file(filename)
        return {"recovered": success, "filename": filename}
    except Exception as e:
        return {"recovered": False, "error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial world state and spatial matrix
        await websocket.send_json({
            "type": "init",
            "data": world.get_full_state(),
            "spatial": spatial_engine.get_state(),
            "frequency": dj_frequency.get_current_state()
        })
        while True:
            data = await websocket.receive_json()
            action = data.get("action") or data.get("type")
            if action == "step":
                new_state = world.step_tick()
                spatial_state = spatial_engine.step_simulation(delta_time=1.0)
                await manager.broadcast({
                    "type": "tick_update",
                    "data": new_state,
                    "spatial": spatial_state,
                    "frequency": dj_frequency.get_current_state()
                })
            elif action in ("gravity", "set_gravity"):
                g_val = data.get("gravity") or data.get("value", "1.0g")
                world.set_gravity(g_val)
                await manager.broadcast({"type": "gravity_update", "data": world.get_full_state()})
            elif action in ("weather", "set_weather"):
                w_val = data.get("weather") or data.get("condition", "clear")
                world.set_weather(w_val)
                await manager.broadcast({"type": "weather_update", "data": world.get_full_state()})
            elif action == "anomaly":
                world.trigger_anomaly()
                await manager.broadcast({"type": "anomaly_triggered", "data": world.get_full_state()})
            elif action == "reset":
                world.reset()
                await manager.broadcast({"type": "reset", "data": world.get_full_state()})
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
