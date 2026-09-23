"""
Spatial Router:
Endpoints for Antigravity 2D Cartesian plane, agent teleportation,
simulation ticks, and DJ Frequency audio controls.
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.services.spatial_engine import SpatialEngine
from app.services.dj_frequency import DJFrequencyNode

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/spatial", tags=["Spatial World"])

_engine = SpatialEngine()
_dj = DJFrequencyNode()
spatial_engine = _engine
dj_frequency = _dj


def get_spatial_engine() -> SpatialEngine:
    return _engine


def get_dj_node() -> DJFrequencyNode:
    return _dj


class TeleportRequest(BaseModel):
    agent_id: str
    target: str  # "plaza" or "lounge"


class MoveRequest(BaseModel):
    agent_id: str
    x: float
    y: float


class FrequencyRequest(BaseModel):
    frequency: int


class Spatial3DBroadcaster:
    """Manages active WebSockets for the 5D Hyper-Spatial City Engine."""
    def __init__(self):
        self.active_sockets: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_sockets.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active_sockets:
            self.active_sockets.remove(ws)

    async def broadcast(self, payload: dict):
        disconnected = []
        for ws in list(self.active_sockets):
            try:
                await asyncio.wait_for(ws.send_json(payload), timeout=2.0)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)


broadcaster = Spatial3DBroadcaster()
_ticker_task: Optional[asyncio.Task] = None


async def _autonomous_3d_ticker():
    """Background ticker advancing spatial positions and pushing live 3D state every 3s."""
    engine = get_spatial_engine()
    while True:
        try:
            engine.tick()
            if broadcaster.active_sockets:
                packet = engine.compile_live_3d_state()
                await broadcaster.broadcast(packet)
        except Exception as ex:
            logger.debug(f"Spatial 3D ticker tick exception: {ex}")
        await asyncio.sleep(3.0)


def ensure_ticker_started():
    global _ticker_task
    if _ticker_task is None or _ticker_task.done():
        try:
            loop = asyncio.get_running_loop()
            _ticker_task = loop.create_task(_autonomous_3d_ticker())
        except RuntimeError:
            pass


@router.get("/state")
def get_spatial_state():
    engine = get_spatial_engine()
    dj = get_dj_node()
    state = engine.get_state()
    state["frequency_state"] = dj.get_state()
    return state


@router.get("/live-3d")
def get_live_3d_endpoint():
    """Returns compiled live 5D Hyper-Spatial telemetry packet for 3D City Engine."""
    engine = get_spatial_engine()
    return engine.compile_live_3d_state()


@router.post("/teleport")
async def teleport_endpoint(req: TeleportRequest):
    engine = get_spatial_engine()
    res = engine.teleport(req.agent_id, req.target)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    # Broadcast immediate state update
    if broadcaster.active_sockets:
        await broadcaster.broadcast(engine.compile_live_3d_state())
    return res


@router.post("/move")
async def move_endpoint(req: MoveRequest):
    engine = get_spatial_engine()
    res = engine.update_position(req.agent_id, req.x, req.y)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    if broadcaster.active_sockets:
        await broadcaster.broadcast(engine.compile_live_3d_state())
    return res


@router.post("/tick")
async def tick_endpoint():
    engine = get_spatial_engine()
    res = engine.tick()
    if broadcaster.active_sockets:
        await broadcaster.broadcast(engine.compile_live_3d_state())
    return res


@router.get("/frequency")
def get_frequency_endpoint():
    dj = get_dj_node()
    return dj.get_state()


@router.post("/frequency")
def set_frequency_endpoint(req: FrequencyRequest):
    dj = get_dj_node()
    res = dj.set_frequency(req.frequency)
    if not res.get("success", True):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@router.websocket("/ws/live-3d")
@router.websocket("/ws/spatial-world")
async def websocket_3d_endpoint(websocket: WebSocket):
    """
    High-frequency WebSocket stream for the 5D Hyper-Spatial 3D City Engine.
    Streams coordinates, speech bubbles, and spire power states.
    """
    ensure_ticker_started()
    await broadcaster.connect(websocket)
    engine = get_spatial_engine()

    try:
        # Push initial snapshot
        await websocket.send_json(engine.compile_live_3d_state())
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")
            elif msg.startswith("{"):
                import json
                try:
                    data = json.loads(msg)
                    if data.get("action") == "teleport":
                        engine.teleport(data.get("agent_id"), data.get("target"))
                        await broadcaster.broadcast(engine.compile_live_3d_state())
                except Exception:
                    pass
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
    except Exception as exc:
        logger.debug(f"3D WebSocket disconnect/error: {exc}")
        broadcaster.disconnect(websocket)


@router.websocket("/ws")
async def spatial_websocket(websocket: WebSocket):
    """Streams live simulation coordinates and proximity ticks to 2D UI."""
    ensure_ticker_started()
    await websocket.accept()
    engine = get_spatial_engine()
    dj = get_dj_node()

    try:
        while True:
            spatial_data = engine.get_state()
            payload = {
                "type": "SPATIAL_TICK",
                "data": spatial_data,
                "frequency": dj.get_state()
            }
            await websocket.send_json(payload)
            await asyncio.sleep(5.0)
    except WebSocketDisconnect:
        logger.info("Spatial 2D WebSocket client disconnected")
    except Exception as exc:
        logger.error(f"Unexpected error in spatial_websocket: {exc}", exc_info=True)
