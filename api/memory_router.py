import logging
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from services.ledger_service import (
    LedgerService,
    LedgerError,
    InsufficientBalanceError,
    AgentNotFoundError,
    InvalidTransactionError
)

logger = logging.getLogger("MemoryRouter")

router = APIRouter(prefix="/api/v1", tags=["Ledger & Semantic Memory Recall"])

# Global shared instance of LedgerService
ledger_service = LedgerService()

# Request Models
class MemoryIndexRequest(BaseModel):
    agent_id: str = Field(..., description="Agent ID who owns or observed the memory")
    memory_id: str = Field(..., description="Unique memory ID")
    content: str = Field(..., description="Text content of the memory")
    embedding: Optional[List[float]] = Field(None, description="Optional 1536-dim vector")
    importance: int = Field(5, ge=1, le=10, description="Memory importance scale 1-10")
    source: str = Field("Observation", description="Source of memory")
    tags: List[str] = Field(default_factory=list, description="Categorization tags")

class TokenTransferRequest(BaseModel):
    sender_id: str = Field(..., description="Sender Agent ID")
    recipient_id: str = Field(..., description="Recipient Agent ID")
    amount: float = Field(..., gt=0, description="Transfer amount (> 0)")
    fee: float = Field(0.0, ge=0, description="Optional gas/network fee")
    memo: str = Field("", description="Transaction memo or purpose")
    signature: Optional[str] = Field(None, description="Cryptographic signature")

# Endpoints: Memory
@router.post("/memory/index", summary="Index Memory into Vector Store")
async def index_memory_endpoint(req: MemoryIndexRequest):
    """Stores and indexes an agent memory with vector embeddings."""
    try:
        res = ledger_service.index_memory(
            agent_id=req.agent_id,
            memory_id=req.memory_id,
            content=req.content,
            embedding=req.embedding,
            importance=req.importance,
            source=req.source,
            tags=req.tags
        )
        return res
    except Exception as e:
        logger.error(f"Error indexing memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory/recall", summary="Semantic Vector Memory Recall")
async def recall_memories_endpoint(
    query: str = Query(..., description="Natural language search query"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    top_k: int = Query(5, ge=1, le=50, description="Max memories to return"),
    min_similarity: float = Query(-1.0, ge=-1.0, le=1.0, description="Minimum cosine similarity cutoff")
):
    """
    Performs cosine similarity search against stored embeddings, ranking memories
    by similarity and importance score.
    """
    try:
        memories = ledger_service.recall_memories(
            agent_id=agent_id,
            query=query,
            top_k=top_k,
            min_similarity=min_similarity
        )
        return {
            "query": query,
            "filter_agent_id": agent_id,
            "count": len(memories),
            "memories": memories
        }
    except Exception as e:
        logger.error(f"Error recalling memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoints: Ledger
@router.get("/ledger/balance/{agent_id}", summary="Get Agent Ledger Account & Balance")
async def get_agent_balance(agent_id: str):
    """Returns token balance, level, and reputation for an agent."""
    account = ledger_service.get_account(agent_id)
    return account

@router.post("/ledger/transfer", summary="Execute Peer-to-Peer Token Transfer")
async def transfer_tokens_endpoint(req: TokenTransferRequest):
    """
    Executes an atomic double-entry transfer from sender to recipient.
    Validates balance sufficiency and records audit transaction.
    """
    try:
        tx = ledger_service.transfer_tokens(
            sender_id=req.sender_id,
            recipient_id=req.recipient_id,
            amount=req.amount,
            memo=req.memo,
            fee=req.fee,
            signature=req.signature
        )
        return tx
    except InsufficientBalanceError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except InvalidTransactionError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except LedgerError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Transfer error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ledger/transactions", summary="List Ledger Transaction History")
async def list_transactions(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return")
):
    """Returns chronological audit records of confirmed token transactions."""
    return {
        "count": len(ledger_service.get_transactions(agent_id=agent_id, limit=limit)),
        "transactions": ledger_service.get_transactions(agent_id=agent_id, limit=limit)
    }
