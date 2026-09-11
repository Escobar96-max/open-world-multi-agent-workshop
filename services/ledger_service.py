import os
import time
import math
import secrets
import threading
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

import numpy as np

logger = logging.getLogger("LedgerService")

class LedgerError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class InsufficientBalanceError(LedgerError):
    def __init__(self, message: str = "Insufficient balance for transfer."):
        super().__init__(message, status_code=400)

class AgentNotFoundError(LedgerError):
    def __init__(self, message: str = "Agent not found in ledger."):
        super().__init__(message, status_code=404)

class InvalidTransactionError(LedgerError):
    def __init__(self, message: str = "Invalid transaction parameters."):
        super().__init__(message, status_code=400)


import re
import hashlib

def generate_deterministic_embedding(text: str, dim: int = 1536) -> List[float]:
    """
    Generates a deterministic normalized mock embedding of dimension `dim`
    derived from token and subword feature hashing (using hashlib.md5).
    Guarantees that semantically overlapping texts have high cosine similarity.
    """
    vec = np.zeros(dim, dtype=np.float32)
    tokens = re.findall(r'\w+', text.lower())
    if not tokens:
        return vec.tolist()

    for tok in tokens:
        # Deterministic token hashing
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if ((h >> 16) % 2 == 0) else -1.0
        vec[idx] += sign * 2.0

        # Subword trigrams for morphological similarity
        if len(tok) >= 3:
            for i in range(len(tok) - 2):
                gram = tok[i:i+3]
                gh = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
                g_idx = gh % dim
                g_sign = 1.0 if ((gh >> 16) % 2 == 0) else -1.0
                vec[g_idx] += g_sign * 0.5

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


class LedgerService:
    """
    Dual-mode Token Ledger & Vector Memory Storage.
    Supports atomic double-entry balance accounting, fraud prevention,
    and high-dimensional semantic vector recall.
    """
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self._lock = threading.Lock()

        # In-memory storage for local/test resilience
        # {agent_id: {"balance": float, "reputation": float, "level": int, "created_at": str}}
        self.accounts: Dict[str, Dict[str, Any]] = {}
        # List of transaction records
        self.transactions: List[Dict[str, Any]] = []
        # In-memory vector store: List[Dict[str, Any]]
        # each has: {agent_id, memory_id, content, embedding, importance, source, tags, created_at}
        self.memories: List[Dict[str, Any]] = []

        # Seed initial foundational agents
        self.register_agent("Sentinel_Alpha", initial_balance=500.0)
        self.register_agent("Curator_Node", initial_balance=500.0)
        self.register_agent("Architect_Prime", initial_balance=1000.0)

    def register_agent(
        self,
        agent_id: str,
        initial_balance: float = 100.0,
        reputation: float = 10.0,
        level: int = 1
    ) -> Dict[str, Any]:
        """Registers a new agent in the ledger with initial token endowment."""
        with self._lock:
            if agent_id in self.accounts:
                return self.accounts[agent_id]

            now_iso = datetime.now(timezone.utc).isoformat()
            account = {
                "agent_id": agent_id,
                "balance": float(initial_balance),
                "reputation": float(reputation),
                "level": level,
                "created_at": now_iso,
                "updated_at": now_iso
            }
            self.accounts[agent_id] = account
            logger.info(f"💰 Registered agent '{agent_id}' in ledger with balance {initial_balance}.")
            return account

    def get_account(self, agent_id: str) -> Dict[str, Any]:
        with self._lock:
            if agent_id not in self.accounts:
                # Auto-register with default balance if not present
                return self.register_agent(agent_id, initial_balance=100.0)
            return dict(self.accounts[agent_id])

    def get_balance(self, agent_id: str) -> float:
        return self.get_account(agent_id)["balance"]

    def transfer_tokens(
        self,
        sender_id: str,
        recipient_id: str,
        amount: float,
        memo: str = "",
        fee: float = 0.0,
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes an atomic double-entry token transfer from sender to recipient.
        Enforces balance sufficiency, self-transfer prohibition, and generates an audit record.
        """
        if sender_id == recipient_id:
            raise InvalidTransactionError("Cannot transfer tokens to self.")
        
        try:
            amt = float(amount)
            f = float(fee)
        except (ValueError, TypeError):
            raise InvalidTransactionError("Amount and fee must be valid numbers.")

        if amt <= 0:
            raise InvalidTransactionError(f"Transfer amount must be positive. Received: {amt}")
        if f < 0:
            raise InvalidTransactionError(f"Transaction fee cannot be negative. Received: {f}")

        total_deduction = amt + f

        with self._lock:
            if sender_id not in self.accounts:
                self.register_agent(sender_id, initial_balance=100.0)
            if recipient_id not in self.accounts:
                self.register_agent(recipient_id, initial_balance=100.0)

            sender_acc = self.accounts[sender_id]
            recipient_acc = self.accounts[recipient_id]

            if sender_acc["balance"] < total_deduction:
                raise InsufficientBalanceError(
                    f"Insufficient funds: Agent '{sender_id}' has {sender_acc['balance']:.4f} tokens, "
                    f"but needs {total_deduction:.4f} (amount: {amt:.4f} + fee: {f:.4f})."
                )

            # Atomic balance update
            sender_acc["balance"] = round(sender_acc["balance"] - total_deduction, 4)
            recipient_acc["balance"] = round(recipient_acc["balance"] + amt, 4)
            
            now_iso = datetime.now(timezone.utc).isoformat()
            sender_acc["updated_at"] = now_iso
            recipient_acc["updated_at"] = now_iso

            tx_id = f"tx_{int(time.time())}_{secrets.token_hex(4)}"
            tx_record = {
                "tx_id": tx_id,
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "amount": amt,
                "fee": f,
                "memo": memo,
                "signature": signature or f"sig_mock_{secrets.token_hex(6)}",
                "status": "CONFIRMED",
                "created_at": now_iso,
                "sender_balance_after": sender_acc["balance"],
                "recipient_balance_after": recipient_acc["balance"]
            }
            self.transactions.append(tx_record)
            logger.info(f"💸 Transfer: {sender_id} -> {recipient_id} | Amount: {amt} | Tx: {tx_id}")
            return tx_record

    def get_transactions(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Returns recent transactions, optionally filtered by agent."""
        with self._lock:
            txs = self.transactions
            if agent_id:
                txs = [t for t in txs if t["sender_id"] == agent_id or t["recipient_id"] == agent_id]
            return sorted(txs, key=lambda x: x["created_at"], reverse=True)[:limit]

    # -------------------------------------------------------------------------
    # Semantic Memory Ingestion & Vector Cosine Recall
    # -------------------------------------------------------------------------

    def index_memory(
        self,
        agent_id: str,
        memory_id: str,
        content: str,
        embedding: Optional[List[float]] = None,
        importance: int = 5,
        source: str = "Observation",
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Stores an episodic or factual memory with high-dimensional vector embedding.
        """
        if not embedding:
            embedding = generate_deterministic_embedding(content)

        importance_clamped = max(1, min(10, importance))
        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            "agent_id": agent_id,
            "memory_id": memory_id,
            "content": content,
            "embedding": embedding,
            "importance": importance_clamped,
            "source": source,
            "tags": tags or [],
            "created_at": now_iso
        }

        with self._lock:
            # Overwrite or append
            self.memories = [m for m in self.memories if m["memory_id"] != memory_id]
            self.memories.append(record)

        logger.info(f"🧠 Indexed memory '{memory_id}' for agent '{agent_id}' (length: {len(content)} chars).")
        return {
            "status": "INDEXED",
            "memory_id": memory_id,
            "agent_id": agent_id,
            "vector_dimension": len(embedding),
            "importance": importance_clamped
        }

    def recall_memories(
        self,
        agent_id: Optional[str] = None,
        query: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        top_k: int = 5,
        min_similarity: float = -1.0
    ) -> List[Dict[str, Any]]:
        """
        Calculates cosine similarity between query embedding and stored memories.
        Ranks results combining similarity and memory importance score.
        """
        if not query_embedding:
            if not query:
                raise LedgerError("Must provide either 'query' text or 'query_embedding'.")
            query_embedding = generate_deterministic_embedding(query)

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm > 0:
            q_vec = q_vec / q_norm

        with self._lock:
            candidates = self.memories
            if agent_id:
                candidates = [m for m in candidates if m["agent_id"] == agent_id]

        if not candidates:
            return []

        scored_results = []
        for mem in candidates:
            m_vec = np.array(mem["embedding"], dtype=np.float32)
            m_norm = np.linalg.norm(m_vec)
            if m_norm > 0:
                m_vec = m_vec / m_norm
            similarity = float(np.dot(q_vec, m_vec))

            if similarity >= min_similarity:
                # Combined ranking score: similarity boosted by importance (1..10)
                importance_factor = 1.0 + (mem["importance"] / 20.0)
                combined_score = round(similarity * importance_factor, 4)

                scored_results.append({
                    "memory_id": mem["memory_id"],
                    "agent_id": mem["agent_id"],
                    "content": mem["content"],
                    "similarity": round(similarity, 4),
                    "combined_score": combined_score,
                    "importance": mem["importance"],
                    "source": mem["source"],
                    "tags": mem["tags"],
                    "created_at": mem["created_at"]
                })

        # Sort descending by combined_score
        scored_results.sort(key=lambda x: x["combined_score"], reverse=True)
        return scored_results[:top_k]
