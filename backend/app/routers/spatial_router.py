"""
Spatial Router:
Endpoints for Antigravity 2D Cartesian plane, agent teleportation,
simulation ticks, and DJ Frequency audio controls.
"""

import asyncio
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.services.spatial_engine import SpatialEngine
from app.services.dj_frequency import DJFrequencyNode

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


@router.get("/state")
def get_spatial_state():
    engine = get_spatial_engine()
    dj = get_dj_node()
    state = engine.get_state()
    state["frequency_state"] = dj.get_state()
    return state


@router.post("/teleport")
def teleport_endpoint(req: TeleportRequest):
    engine = get_spatial_engine()
    res = engine.teleport(req.agent_id, req.target)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@router.post("/move")
def move_endpoint(req: MoveRequest):
    engine = get_spatial_engine()
    res = engine.update_position(req.agent_id, req.x, req.y)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@router.post("/tick")
def tick_endpoint():
    engine = get_spatial_engine()
    return engine.tick()


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


@router.websocket("/ws")
async def spatial_websocket(websocket: WebSocket):
    """Streams live simulation coordinates and proximity ticks to the UI."""
    await websocket.accept()
    engine = get_spatial_engine()
    dj = get_dj_node()

    try:
        while True:
            tick_data = engine.tick()
            payload = {
                "type": "SPATIAL_TICK",
                "data": tick_data,
                "frequency": dj.get_state()
            }
            await websocket.send_json(payload)
            await asyncio.sleep(5.0)
    except WebSocketDisconnect:
        logger_msg = "WebSocket client disconnected"
    except Exception:
        pass
