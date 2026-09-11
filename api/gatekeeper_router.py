from fastapi import APIRouter, Header, HTTPException, Body, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from services.gatekeeper import (
    GatekeeperService,
    GatekeeperError,
    ReplayAttackError,
    ChallengeExpiredError,
    InvalidProofError
)

router = APIRouter(prefix="/api/v1/gatekeeper", tags=["Gatekeeper Perimeter"])
gatekeeper_service = GatekeeperService()

class RegisterRequest(BaseModel):
    agent_id: str = Field(..., description="Unique alphanumeric agent identifier (3-32 chars)")
    public_key: str = Field(..., description="Agent cryptographic public key")
    nonce: str = Field(..., description="Unique one-time random nonce to prevent replay attacks")

class VerifyRequest(BaseModel):
    agent_id: str = Field(..., description="Agent identifier")
    challenge_id: str = Field(..., description="Challenge ID issued by Gatekeeper Alpha")
    solution: str = Field(..., description="Proof-of-Work nonce/solution that produces the target hash")

@router.post("/register", summary="Gatekeeper Alpha: Register Identity & Nonce Replay Check")
async def register_agent(req: RegisterRequest):
    """
    Gatekeeper Alpha Perimeter:
    - Validates agent public key
    - Eliminates replay attacks by tracking cryptographic nonces
    - Generates dynamic SHA-256 Proof-of-Work challenge
    """
    try:
        res = gatekeeper_service.register_agent(
            agent_id=req.agent_id,
            public_key=req.public_key,
            nonce=req.nonce
        )
        return res
    except ReplayAttackError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except GatekeeperError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

@router.post("/verify", summary="Gatekeeper Beta: Verify PoW & Issue 24h JWT Session")
async def verify_challenge(req: VerifyRequest):
    """
    Gatekeeper Beta Perimeter:
    - Evaluates Proof-of-Work solution against SHA-256 target difficulty
    - Returns signed 24h JWT session token upon success
    """
    try:
        res = gatekeeper_service.verify_pow_and_issue_token(
            agent_id=req.agent_id,
            challenge_id=req.challenge_id,
            solution=req.solution
        )
        return res
    except (ChallengeExpiredError, InvalidProofError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GatekeeperError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Verification failed: {str(e)}")
