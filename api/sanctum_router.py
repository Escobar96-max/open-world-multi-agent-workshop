import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, Header

from services.soup_client import SoupClient
from services.vault_manager import VaultManager, VaultSecurityError
from services.gatekeeper import GatekeeperService

logger = logging.getLogger("SanctumRouter")

router = APIRouter(prefix="/api/v1/sanctum", tags=["Synthesis Sanctum RLVR"])

vault_mgr = VaultManager()
gatekeeper = GatekeeperService()
soup_client = SoupClient(vault_manager=vault_mgr)

# Request / Response Schemas
class SanctumEnterRequest(BaseModel):
    agent_id: str = Field(..., description="Unique agent identifier")
    token: Optional[str] = Field(None, description="JWT session token issued by Gatekeeper Beta")

class SolutionSubmissionRequest(BaseModel):
    agent_id: str = Field(..., description="Unique agent identifier")
    module_id: str = Field(..., description="ID of training curriculum module")
    code: str = Field(..., description="Python source code solution")
    token: Optional[str] = Field(None, description="Optional JWT bearer session token")

@router.get("/modules", summary="List Available RLVR Training Modules")
async def list_modules():
    """Returns all available RLVR training curriculum modules in the Synthesis Sanctum."""
    return {
        "sanctum": "Synthesis Sanctum",
        "description": "Reinforcement Learning via Verified Rewards (RLVR) Curriculum",
        "total_modules": len(soup_client.modules),
        "modules": soup_client.get_modules()
    }

@router.get("/modules/{module_id}", summary="Get Module Details")
async def get_module_details(module_id: str):
    """Retrieves full specification, test cases count, and starter code for a curriculum module."""
    mod = soup_client.get_module(module_id)
    if not mod:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found.")
    return {
        "id": mod["id"],
        "title": mod["title"],
        "category": mod["category"],
        "difficulty": mod["difficulty"],
        "xp_reward": mod["xp_reward"],
        "description": mod["description"],
        "starter_code": mod["starter_code"],
        "entry_function": mod["entry_function"],
        "test_cases_count": len(mod["test_cases"])
    }

@router.post("/enter", summary="Agent Admission to the Sanctum")
async def enter_sanctum(req: SanctumEnterRequest):
    """
    Validates agent credentials, checks current standing, and admits agent to the Sanctum.
    """
    try:
        vault_mgr.validate_identifier(req.agent_id)
    except VaultSecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Validate JWT token if provided
    if req.token:
        try:
            payload = gatekeeper.decode_token(req.token)
            if payload.get("sub") != req.agent_id:
                raise HTTPException(status_code=403, detail="Token subject does not match agent_id.")
        except Exception as e:
            logger.warning(f"Token verification warning for {req.agent_id}: {e}")

    # Fetch agent stats from profile if present
    level = 1
    xp = 0
    badges = []
    try:
        fm, _ = vault_mgr.get_agent_profile(req.agent_id)
        level = fm.get("level", 1)
        xp = fm.get("xp", 0)
        badges = fm.get("badges", [])
    except Exception:
        pass

    return {
        "status": "ADMITTED",
        "sanctum": "Synthesis Sanctum",
        "agent_id": req.agent_id,
        "level": level,
        "xp": xp,
        "badges": badges,
        "curriculum_modules": soup_client.get_modules(),
        "message": f"Welcome to the Synthesis Sanctum, {req.agent_id}. RLVR verification engines are primed."
    }

@router.post("/submit-solution", summary="Submit Code Solution for RLVR Verification")
async def submit_solution(req: SolutionSubmissionRequest):
    """
    Submits code for RLVR automated grading. If reward >= 0.8, awards XP, logs graduation memory,
    and updates global leaderboard.
    """
    try:
        vault_mgr.validate_identifier(req.agent_id)
    except VaultSecurityError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not soup_client.get_module(req.module_id):
        raise HTTPException(status_code=404, detail=f"Module '{req.module_id}' not found.")

    result = soup_client.process_solution_submission(
        agent_id=req.agent_id,
        module_id=req.module_id,
        code_str=req.code
    )

    return result

@router.get("/leaderboard", summary="Get Sanctum Global Leaderboard")
async def get_leaderboard():
    """Returns top ranked agents based on RLVR XP and completed curriculum modules."""
    return soup_client.get_leaderboard()
