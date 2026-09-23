"""
Agent Training Ground Router:
Exposes REST endpoints for the Agent Profiles & Training Ground panel.
Provides agent inspection, multi-source ingestion training launch, and live progress polling.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.services.training_ground import training_ground

router = APIRouter(prefix="/api/v1/training", tags=["Agent Training Ground"])


class StartTrainingRequest(BaseModel):
    agent_id: str
    topic: str
    task: Optional[str] = "Implement and verify architecture benchmark"


@router.get("/agents")
def list_agents_endpoint() -> List[Dict[str, Any]]:
    """Lists all active agents with their current roles, specializations, and training states."""
    return training_ground.list_all_agents()


@router.get("/agent/{agent_id}")
def get_agent_profile_endpoint(agent_id: str) -> Dict[str, Any]:
    """Retrieves full profile, acquired skills, and active training status for a specific agent."""
    return training_ground.get_agent_profile(agent_id)


@router.get("/status/{agent_id}")
def get_agent_training_status_endpoint(agent_id: str) -> Dict[str, Any]:
    """Lightweight polling endpoint for real-time progress bar and stage updates."""
    profile = training_ground.get_agent_profile(agent_id)
    return {
        "agent_id": profile["agent_id"],
        "current_topic": profile["current_topic"],
        "progress_pct": profile["progress_pct"],
        "current_stage": profile["current_stage"],
        "stages_completed": profile["stages_completed"],
        "logs": profile["logs"]
    }


@router.post("/assign")
async def assign_training_endpoint(req: StartTrainingRequest, bg: BackgroundTasks):
    """
    Assigns a new multi-source training topic to an agent.
    Launches Web Search & Doc Extraction -> YouTube Video Transcript Digest ->
    Soup Zero RLVR Deterministic Pytest Sandbox -> Obsidian Profile Sync.
    """
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="Training topic cannot be empty.")

    # Launch non-blocking background training loop
    bg.add_task(
        training_ground.launch_agent_training,
        req.agent_id,
        req.topic.strip(),
        req.task or "Verify architectural implementation"
    )

    return {
        "status": "started",
        "agent_id": req.agent_id,
        "topic": req.topic.strip(),
        "task": req.task,
        "message": f"Training initiated for [[{req.agent_id}]]. Ingesting Web Docs + YouTube Transcripts."
    }
