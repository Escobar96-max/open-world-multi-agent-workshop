import os
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from services.spatial_engine import SpatialEngine
from services.dj_frequency import DJFrequencyNode, SUPPORTED_FREQUENCIES
from services.lounge_manager import LoungeManager
from services.vault_manager import VaultManager

router = APIRouter(prefix="/api/v1", tags=["Spatial Simulation & Frequency Lounge"])

vault_mgr = VaultManager()
spatial_engine = SpatialEngine(vault_manager=vault_mgr)
dj_frequency = DJFrequencyNode(initial_frequency=432)
lounge_mgr = LoungeManager(vault_manager=vault_mgr)

class TeleportRequest(BaseModel):
    agent_id: str = Field(..., description="Agent identifier to teleport")
    x: float = Field(..., ge=0.0, le=100.0, description="X coordinate (0.0 to 100.0)")
    y: float = Field(..., ge=0.0, le=100.0, description="Y coordinate (0.0 to 100.0)")
    admin_key: Optional[str] = Field(None, description="Admin secret key")

class FrequencyShiftRequest(BaseModel):
    frequency_hz: int = Field(..., description="Target frequency (432, 528, or 40)")
    reason: Optional[str] = Field("Operator C2 Frequency Shift", description="Reason for frequency adjustment")
    admin_key: Optional[str] = Field(None, description="Admin secret key")

class LoungeDialogueRequest(BaseModel):
    speaker_id: str = Field(..., description="Speaker agent_id")
    message: str = Field(..., description="Dialogue message")
    listener_id: Optional[str] = Field(None, description="Optional listener agent_id")

def _verify_admin(admin_key: Optional[str], header_key: Optional[str]):
    expected = os.getenv("ADMIN_SECRET_KEY", "op_secret_master_key_9921")
    provided = header_key or admin_key
    if not provided or provided != expected:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid ADMIN_SECRET_KEY.")

# ================= SPATIAL ENDPOINTS =================

@router.get("/spatial/state", summary="Current 2D Spatial Engine State")
async def get_spatial_state():
    state = spatial_engine.get_state()
    # Enrich agents with current dynamic frequency temperature
    for agent in state["agents"]:
        agent["dynamic_temperature"] = dj_frequency.calculate_cognitive_temperature(agent["zone"])
    return state

@router.post("/spatial/teleport", summary="Teleport Agent to Coordinates")
async def teleport_agent(
    req: TeleportRequest,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
):
    _verify_admin(req.admin_key, x_admin_key)
    try:
        updated = spatial_engine.teleport_agent(req.agent_id, req.x, req.y)
        updated["dynamic_temperature"] = dj_frequency.calculate_cognitive_temperature(updated["zone"])
        return {
            "status": "SUCCESS",
            "agent": updated
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/spatial/step", summary="Advance Spatial Engine Simulation by 1 Tick")
async def step_spatial():
    tick_result = spatial_engine.step_simulation(delta_time=1.0)
    return tick_result

# ================= FREQUENCY LOUNGE ENDPOINTS =================

@router.get("/lounge/frequency", summary="Active DJ Acoustic Frequency Status")
async def get_frequency_state():
    return dj_frequency.get_current_state()

@router.post("/lounge/frequency", summary="Shift Active DJ Acoustic Frequency")
async def set_frequency(
    req: FrequencyShiftRequest,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
):
    _verify_admin(req.admin_key, x_admin_key)
    try:
        state = dj_frequency.set_frequency(req.frequency_hz, reason=req.reason or "Operator Shift")
        return {
            "status": "SUCCESS",
            "frequency_state": state
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/lounge/logs", summary="Recent Lounge Dialogue Logs")
async def get_lounge_logs(limit: int = 20):
    logs = lounge_mgr.get_recent_logs(limit=limit)
    return {
        "count": len(logs),
        "logs": logs
    }

@router.post("/lounge/dialogue", summary="Record Lounge Dialogue Turn")
async def post_lounge_dialogue(req: LoungeDialogueRequest):
    try:
        # Check if speaker is in lounge
        agent = spatial_engine.agents.get(req.speaker_id)
        zone = agent["zone"] if agent else "Frequency Lounge"
        temp = dj_frequency.calculate_cognitive_temperature(zone)
        
        result = lounge_mgr.record_dialogue(
            speaker_id=req.speaker_id,
            message=req.message,
            frequency_hz=dj_frequency.current_frequency,
            listener_id=req.listener_id,
            temperature=temp
        )
        return {
            "status": "SUCCESS",
            "entry": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
