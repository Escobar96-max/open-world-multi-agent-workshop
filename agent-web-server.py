import sys
import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("AgentWebServer")

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sim_engine import GravitonWorld

import uvicorn
from fastapi import FastAPI, BackgroundTasks, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Initialize Singleton World
world = GravitonWorld()

# Background Loop Control
loop_state = {
    "is_running": True,
    "interval_seconds": 2.0,
    "task": None
}

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"🔌 WebSocket Client Connected. Total clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"🔌 WebSocket Client Disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.disconnect(d)

manager = ConnectionManager()

async def background_simulation_loop():
    """Autonomous background tick execution loop with WebSocket broadcast."""
    logger.info("🚀 Background Simulation Loop initiated.")
    while True:
        try:
            if loop_state["is_running"]:
                state = world.step_tick()
                logger.info(f"⏱️ [BACKGROUND TICK {state['tick']:02d}] Gravity: {state['local_gravity']} | Weather: {state.get('weather', {}).get('condition', 'clear')} | Core Stability: {state['core_stability']}%")
                await manager.broadcast({
                    "type": "tick_update",
                    "data": state
                })
            await asyncio.sleep(loop_state["interval_seconds"])
        except asyncio.CancelledError:
            logger.info("🛑 Background Simulation Loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in background loop: {e}")
            await asyncio.sleep(loop_state["interval_seconds"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background simulation loop
    loop_task = asyncio.create_task(background_simulation_loop())
    loop_state["task"] = loop_task
    logger.info("⚡ FastAPI Agent Web Server started successfully on port 8080.")
    yield
    # Shutdown: Cancel background loop
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass
    logger.info("🛑 Server shutdown complete.")

app = FastAPI(
    title="Anti-Gravity Multi-Agent Simulation API",
    description="FastAPI gateway managing physics, InfluenceMap calculations, AgentSafetyGateway, and Obsidian Daily Logs",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for React dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "service": "Anti-Gravity Multi-Agent FastAPI Server",
        "status": "online",
        "port": 8080,
        "websocket_endpoint": "/ws",
        "background_loop_active": loop_state["is_running"],
        "tick": world.tick
    }

@app.get("/api/status")
def get_status():
    return {
        "status": "healthy",
        "tick": world.tick,
        "location": world.location,
        "local_gravity": world.local_gravity,
        "weather": getattr(world, "weather", {}),
        "core_stability": world.core_stability,
        "loop_running": loop_state["is_running"],
        "loop_interval": loop_state["interval_seconds"]
    }

@app.get("/api/state")
def get_world_state():
    return world.get_full_state()

@app.post("/api/step")
async def manual_step():
    new_state = world.step_tick()
    logger.info(f"⚡ [MANUAL STEP] Advanced to Tick {new_state['tick']:02d}")
    await manager.broadcast({"type": "tick_update", "data": new_state})
    return new_state

@app.post("/api/gravity")
async def set_gravity(payload: Dict[str, Any] = Body(...)):
    g_str = payload.get("gravity", "1.0g")
    world.set_gravity(g_str)
    logger.info(f"🎛️ [GRAVITY OVERRIDE] Set to {g_str}")
    state = world.get_full_state()
    await manager.broadcast({"type": "gravity_update", "data": state})
    return state

@app.post("/api/weather")
async def set_weather(payload: Dict[str, Any] = Body(...)):
    cond = payload.get("condition", "clear")
    world.set_weather(cond)
    logger.info(f"🌦️ [WEATHER OVERRIDE] Set to {cond}")
    state = world.get_full_state()
    await manager.broadcast({"type": "weather_update", "data": state})
    return state

@app.post("/api/anomaly")
async def trigger_anomaly():
    world.trigger_anomaly()
    logger.warning("⚠️ [ANOMALY TRIGGERED] Singularity mass inversion active (-1.2g)!")
    state = world.get_full_state()
    await manager.broadcast({"type": "anomaly_triggered", "data": state})
    return state

@app.post("/api/reset")
async def reset_world():
    world.reset()
    logger.info("🔄 [RESET] Simulation world restored to initial coordinates.")
    state = world.get_full_state()
    await manager.broadcast({"type": "reset", "data": state})
    return state

@app.post("/api/loop/toggle")
def toggle_background_loop(payload: Optional[Dict[str, Any]] = Body(None)):
    if payload and "active" in payload:
        loop_state["is_running"] = bool(payload["active"])
    else:
        loop_state["is_running"] = not loop_state["is_running"]
    logger.info(f"🔁 Background simulation loop set to: {loop_state['is_running']}")
    return {"loop_running": loop_state["is_running"], "interval": loop_state["interval_seconds"]}

# =====================================================================
# MEMORY CONSOLIDATION ENDPOINTS
# =====================================================================
@app.get("/api/memory/stats")
def memory_stats():
    """Returns cognitive buffer sizes, node counts, and token optimization metrics."""
    try:
        from agent_memory_consolidator import get_memory_stats
        return get_memory_stats()
    except Exception as e:
        logger.error(f"Error fetching memory stats: {e}")
        return {"error": str(e), "hot_count": 0, "cold_count": 0, "tombstone_count": 0}

@app.post("/api/memory/consolidate")
def memory_consolidate():
    """Manual override trigger to immediately execute dual-buffer consolidation."""
    try:
        from agent_memory_consolidator import MemoryConsolidator
        consolidator = MemoryConsolidator()
        result = consolidator.run_consolidation_cycle()
        return result
    except Exception as e:
        logger.error(f"Error running consolidation cycle: {e}")
        return {"status": "error", "error": str(e)}

@app.post("/api/memory/recover")
def memory_recover(payload: Dict[str, Any] = Body(...)):
    """Restores target file from Tombstone archive back to active episodic buffer."""
    try:
        from agent_memory_consolidator import recover_tombstoned_file
        filename = payload.get("filename", "")
        success = recover_tombstoned_file(filename)
        return {"recovered": success, "filename": filename}
    except Exception as e:
        logger.error(f"Error recovering tombstoned memory: {e}")
        return {"recovered": False, "error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Send initial snapshot immediately upon connecting
    initial_state = world.get_full_state()
    await websocket.send_json({
        "type": "initial_state",
        "data": initial_state
    })
    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                data = json.loads(raw_msg)
                action = data.get("action") or data.get("type")
                if action == "step":
                    new_state = world.step_tick()
                    await manager.broadcast({"type": "tick_update", "data": new_state})
                elif action == "gravity" or action == "set_gravity":
                    g_val = data.get("gravity") or data.get("value", "1.0g")
                    world.set_gravity(g_val)
                    await manager.broadcast({"type": "gravity_update", "data": world.get_full_state()})
                elif action == "weather" or action == "set_weather":
                    w_val = data.get("condition") or data.get("weather", "clear")
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
            except Exception as e:
                logger.error(f"WebSocket incoming message processing error: {e}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🚀 LAUNCHING AGENT-WEB-SERVER.PY (FASTAPI + WEBSOCKETS '/ws' STREAM)")
    print("📍 Host: 127.0.0.1 | Port: 8080 | WebSocket: ws://localhost:8080/ws")
    print("=" * 80 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")
