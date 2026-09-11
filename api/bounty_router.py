import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from services.bounty_manager import BountyManager, BountyError
from services.vault_manager import VaultManager
from services.ledger_service import LedgerService

logger = logging.getLogger("BountyRouter")

router = APIRouter(prefix="/api/v1/bounty", tags=["Task & Bounty Marketplace"])

# Shared manager instance
vault_mgr = VaultManager()
ledger_svc = LedgerService()
bounty_mgr = BountyManager(vault_manager=vault_mgr, ledger_service=ledger_svc)

# Schemas
class BountyCreateRequest(BaseModel):
    title: str = Field(..., description="Short descriptive title of bounty task")
    description: str = Field(..., description="Detailed requirements or acceptance criteria")
    reward: float = Field(..., gt=0, description="Token reward amount")
    posted_by: str = Field(..., description="Agent ID creating the bounty")

class BountyClaimRequest(BaseModel):
    bounty_id: str = Field(..., description="Bounty ID to claim")
    agent_id: str = Field(..., description="Agent ID claiming the task")

class BountySubmitRequest(BaseModel):
    bounty_id: str = Field(..., description="Bounty ID")
    agent_id: str = Field(..., description="Assignee Agent ID submitting work")
    proof_of_work: str = Field(..., description="Proof of work, artifact link, or output data")

class BountyCompleteRequest(BaseModel):
    bounty_id: str = Field(..., description="Bounty ID to finalize")
    verifier_id: str = Field(..., description="Poster, Architect_Prime, or Operator verifying work")

@router.get("/list", summary="List Bounties")
async def list_bounties_endpoint(
    status: Optional[str] = Query(None, description="Filter by status (OPEN, CLAIMED, SUBMITTED, COMPLETED)")
):
    """Retrieves all bounties on the marketplace board."""
    bounties = bounty_mgr.list_bounties(status=status)
    return {
        "count": len(bounties),
        "filter_status": status,
        "bounties": bounties
    }

@router.get("/{bounty_id}", summary="Get Bounty Details")
async def get_bounty_endpoint(bounty_id: str):
    """Retrieves detailed status, description, and history for a specific bounty."""
    try:
        return bounty_mgr.get_bounty(bounty_id)
    except BountyError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.post("/create", summary="Create New Bounty")
async def create_bounty_endpoint(req: BountyCreateRequest):
    """Posts a new bounty task to the marketplace and syncs to Obsidian."""
    try:
        bounty = bounty_mgr.create_bounty(
            title=req.title,
            description=req.description,
            reward=req.reward,
            posted_by=req.posted_by
        )
        return bounty
    except BountyError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error creating bounty: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/claim", summary="Claim an Open Bounty")
async def claim_bounty_endpoint(req: BountyClaimRequest):
    """Assigns an open bounty task to an agent."""
    try:
        bounty = bounty_mgr.claim_bounty(
            bounty_id=req.bounty_id,
            agent_id=req.agent_id
        )
        return bounty
    except BountyError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.post("/submit", summary="Submit Proof of Work for Bounty")
async def submit_bounty_endpoint(req: BountySubmitRequest):
    """Submits completion artifacts or proof of work for review."""
    try:
        bounty = bounty_mgr.submit_bounty_work(
            bounty_id=req.bounty_id,
            agent_id=req.agent_id,
            proof_of_work=req.proof_of_work
        )
        return bounty
    except BountyError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.post("/complete", summary="Approve and Release Bounty Escrow")
async def complete_bounty_endpoint(req: BountyCompleteRequest):
    """Verifies work and releases token escrow payment from poster to assignee."""
    try:
        res = bounty_mgr.complete_bounty(
            bounty_id=req.bounty_id,
            verifier_id=req.verifier_id
        )
        return res
    except BountyError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error completing bounty: {e}")
        raise HTTPException(status_code=500, detail=str(e))
