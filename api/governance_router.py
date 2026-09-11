import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from services.governance_engine import GovernanceEngine, GovernanceError
from services.vault_manager import VaultManager

logger = logging.getLogger("GovernanceRouter")

router = APIRouter(prefix="/api/v1/governance", tags=["Autonomous Co-Governance"])

# Shared engine instance
vault_mgr = VaultManager()
governance_engine = GovernanceEngine(vault_manager=vault_mgr)

# Request Schemas
class ProposalCreateRequest(BaseModel):
    title: str = Field(..., description="Title of the RFC proposal")
    summary: str = Field(..., description="Detailed rationale and summary of proposal")
    proposer_id: str = Field(..., description="Agent ID submitting RFC")
    directives: str = Field("", description="Specific operational or constitutional directives")

class ProposalVoteRequest(BaseModel):
    proposal_id: str = Field(..., description="Target proposal ID")
    agent_id: str = Field(..., description="Voting agent ID")
    choice: str = Field(..., description="'FOR' or 'AGAINST'")

@router.get("/proposals", summary="List Governance RFC Proposals")
async def list_proposals_endpoint(
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, PASSED, REJECTED)")
):
    """Retrieves all community proposals and voting statuses."""
    props = governance_engine.list_proposals(status=status)
    return {
        "count": len(props),
        "consensus_threshold": "75% (3/4)",
        "filter_status": status,
        "proposals": props
    }

@router.get("/proposals/{proposal_id}", summary="Get Proposal Details")
async def get_proposal_endpoint(proposal_id: str):
    """Retrieves full details, votes tally, and enactment status for an RFC."""
    try:
        return governance_engine.get_proposal(proposal_id)
    except GovernanceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.post("/propose", summary="Submit a New RFC Proposal")
async def create_proposal_endpoint(req: ProposalCreateRequest):
    """Submits a new governance proposal for community consensus voting."""
    try:
        prop = governance_engine.submit_proposal(
            title=req.title,
            summary=req.summary,
            proposer_id=req.proposer_id,
            directives=req.directives
        )
        return prop
    except GovernanceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error submitting proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vote", summary="Cast Vote on RFC Proposal")
async def vote_proposal_endpoint(req: ProposalVoteRequest):
    """
    Casts a vote ('FOR' or 'AGAINST') on an active RFC.
    If 3/4 consensus is achieved with quorum, the proposal is enacted immediately.
    """
    try:
        res = governance_engine.cast_vote(
            proposal_id=req.proposal_id,
            agent_id=req.agent_id,
            choice=req.choice
        )
        return res
    except GovernanceError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error voting on proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))
