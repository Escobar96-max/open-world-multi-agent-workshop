"""
Sanctum Router:
Exposes REST endpoints for Soup Zero RLVR Continuous Self-Training Sanctum.
Agents enter the Sanctum to receive adaptive curriculum and submit verified code solutions.
"""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.soup_client import SoupZeroEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sanctum", tags=["Sanctum - Soup Zero RLVR"])

_soup_engine = SoupZeroEngine()


def get_soup_engine() -> SoupZeroEngine:
    return _soup_engine


class EnterSanctumRequest(BaseModel):
    agent_id: str
    desired_skill_domain: str


class SubmitSolutionRequest(BaseModel):
    agent_id: str
    curriculum_id: str
    code_solution: str
    skill_domain: Optional[str] = None


@router.post("/enter")
def enter_sanctum_endpoint(req: EnterSanctumRequest):
    """
    Agent enters the Sanctum for self-training.
    Returns 432Hz harmonic vibe context, recommended temperature, and curriculum.
    """
    engine = get_soup_engine()
    if not req.agent_id.strip():
        raise HTTPException(status_code=400, detail="agent_id cannot be empty.")
    if not req.desired_skill_domain.strip():
        raise HTTPException(status_code=400, detail="desired_skill_domain cannot be empty.")

    try:
        curriculum = engine.initialize_curriculum(
            agent_id=req.agent_id.strip(),
            skill_domain=req.desired_skill_domain.strip()
        )
    except Exception as err:
        logger.error(f"Curriculum initialization error: {err}")
        raise HTTPException(status_code=400, detail="Curriculum initialization failed.")

    # Synchronize with Antigravity 2D Spatial Matrix & 432Hz Frequency Node
    spatial_coords = None
    try:
        from app.routers.spatial_router import spatial_engine, dj_frequency
        spatial_engine.teleport(req.agent_id.strip(), "lounge")
        dj_frequency.set_frequency(432)
        if req.agent_id.strip() in spatial_engine.agents:
            ag = spatial_engine.agents[req.agent_id.strip()]
            spatial_coords = {"x": ag.x, "y": ag.y, "zone": ag.zone, "temperature": ag.temperature}
    except Exception as ex:
        logger.debug(f"Spatial/DJ entrainment synchronization note: {ex}")

    return {
        "status": "active",
        "agent_id": req.agent_id.strip(),
        "desired_skill_domain": req.desired_skill_domain.strip(),
        "vibe_context": "432Hz Harmonic Active",
        "recommended_temp": 0.4,
        "spatial_grid": "[51-100] Frequency Lounge / Synthesis Sanctum",
        "spatial_coords": spatial_coords or {"zone": "Frequency Lounge", "temperature": 1.6},
        "curriculum": curriculum,
        "message": f"[[{req.agent_id}]] entered the Soup Zero Sanctum. Curriculum initialized in 432Hz entrainment field."
    }


@router.post("/submit-solution")
def submit_solution_endpoint(req: SubmitSolutionRequest):
    """
    Submits code solution to Soup Zero for RLVR test verification.
    On 100% pass: awards +5 reputation, injects skill badge in profile, and updates leaderboard.
    """
    engine = get_soup_engine()
    if not req.agent_id.strip() or not req.curriculum_id.strip():
        raise HTTPException(status_code=400, detail="agent_id and curriculum_id are required.")

    try:
        result = engine.verify_solution(
            agent_id=req.agent_id.strip(),
            curriculum_id=req.curriculum_id.strip(),
            code_solution=req.code_solution,
            skill_domain=req.skill_domain
        )
    except Exception as e:
        logger.error(f"Error during solution verification: {e}")
        raise HTTPException(status_code=500, detail="Solution verification failed.")

    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Solution verification failed."))

    return {
        "success": True,
        "verification": result,
        "reputation_gain": result.get("reputation_gain", 5),
        "new_reputation": result.get("new_reputation"),
        "skill_badge": result.get("skill_badge"),
        "obsidian_synced": True,
        "message": f"Verification 100% passed! +{result.get('reputation_gain', 5)} reputation awarded to [[{req.agent_id}]]."
    }
