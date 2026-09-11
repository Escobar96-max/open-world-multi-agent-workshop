import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from services.ledger_service import (
    LedgerService,
    InsufficientBalanceError,
    InvalidTransactionError
)
from api.memory_router import router as memory_router

app = FastAPI()
app.include_router(memory_router)
client = TestClient(app)

@pytest.fixture
def clean_ledger():
    ledger = LedgerService()
    return ledger

def test_initial_accounts_and_registration(clean_ledger):
    acc = clean_ledger.get_account("Sentinel_Alpha")
    assert acc["balance"] == 500.0

    new_acc = clean_ledger.register_agent("Test_Agent_1", initial_balance=250.0)
    assert new_acc["balance"] == 250.0
    assert clean_ledger.get_balance("Test_Agent_1") == 250.0

def test_atomic_token_transfer_and_fees(clean_ledger):
    # Sentinel_Alpha (500) -> Curator_Node (500) transfer 100 with 2 fee
    tx = clean_ledger.transfer_tokens(
        sender_id="Sentinel_Alpha",
        recipient_id="Curator_Node",
        amount=100.0,
        fee=2.0,
        memo="Bounty reward advance"
    )

    assert tx["status"] == "CONFIRMED"
    assert tx["amount"] == 100.0
    assert tx["fee"] == 2.0
    assert clean_ledger.get_balance("Sentinel_Alpha") == 398.0
    assert clean_ledger.get_balance("Curator_Node") == 600.0

    history = clean_ledger.get_transactions(agent_id="Sentinel_Alpha")
    assert len(history) >= 1
    assert history[0]["tx_id"] == tx["tx_id"]

def test_transfer_validation_and_rejections(clean_ledger):
    # 1. Overdraft attempt
    with pytest.raises(InsufficientBalanceError):
        clean_ledger.transfer_tokens("Sentinel_Alpha", "Curator_Node", amount=99999.0)

    # 2. Self transfer
    with pytest.raises(InvalidTransactionError):
        clean_ledger.transfer_tokens("Sentinel_Alpha", "Sentinel_Alpha", amount=50.0)

    # 3. Negative amount
    with pytest.raises(InvalidTransactionError):
        clean_ledger.transfer_tokens("Sentinel_Alpha", "Curator_Node", amount=-10.0)

    # 4. Negative fee
    with pytest.raises(InvalidTransactionError):
        clean_ledger.transfer_tokens("Sentinel_Alpha", "Curator_Node", amount=10.0, fee=-5.0)

def test_semantic_memory_indexing_and_recall(clean_ledger):
    clean_ledger.index_memory(
        agent_id="Sentinel_Alpha",
        memory_id="mem_patrol_001",
        content="Detected unauthorized probe near Gatekeeper Beta coordinate plane at dusk.",
        importance=8,
        tags=["security", "perimeter"]
    )
    clean_ledger.index_memory(
        agent_id="Sentinel_Alpha",
        memory_id="mem_music_002",
        content="Listening to 432Hz ambient solfeggio tone in the Frequency Lounge relaxation pool.",
        importance=4,
        tags=["lounge", "frequency"]
    )
    clean_ledger.index_memory(
        agent_id="Curator_Node",
        memory_id="mem_vault_003",
        content="Cataloged three new governance RFC proposals into the obsidian world vault archive.",
        importance=6,
        tags=["governance", "vault"]
    )

    # Semantic search for security
    results = clean_ledger.recall_memories(
        query="security intrusion detected at gatekeeper",
        top_k=2
    )
    assert len(results) >= 1
    top_hit = results[0]
    assert "mem_patrol_001" == top_hit["memory_id"]
    assert top_hit["combined_score"] > 0

    # Filter by agent_id
    curator_results = clean_ledger.recall_memories(
        agent_id="Curator_Node",
        query="vault archive catalog",
        top_k=5
    )
    assert len(curator_results) == 1
    assert curator_results[0]["agent_id"] == "Curator_Node"
    assert curator_results[0]["memory_id"] == "mem_vault_003"

def test_api_ledger_and_memory_endpoints(monkeypatch):
    from api import memory_router as mr
    test_ledger = LedgerService()
    monkeypatch.setattr(mr, "ledger_service", test_ledger)

    # 1. GET /api/v1/ledger/balance/Sentinel_Alpha
    resp = client.get("/api/v1/ledger/balance/Sentinel_Alpha")
    assert resp.status_code == 200
    assert resp.json()["balance"] == 500.0

    # 2. POST /api/v1/ledger/transfer
    resp = client.post(
        "/api/v1/ledger/transfer",
        json={
            "sender_id": "Sentinel_Alpha",
            "recipient_id": "Curator_Node",
            "amount": 75.0,
            "fee": 1.5,
            "memo": "Knowledge indexing bounty"
        }
    )
    assert resp.status_code == 200
    tx_data = resp.json()
    assert tx_data["amount"] == 75.0
    assert tx_data["sender_balance_after"] == 423.5

    # 3. GET /api/v1/ledger/transactions
    resp = client.get("/api/v1/ledger/transactions?agent_id=Sentinel_Alpha")
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1

    # 4. POST /api/v1/memory/index
    resp = client.post(
        "/api/v1/memory/index",
        json={
            "agent_id": "Sentinel_Alpha",
            "memory_id": "mem_api_test_01",
            "content": "Reinforcement learning training completed with reward 1.0",
            "importance": 9,
            "source": "Sanctum",
            "tags": ["rlvr", "training"]
        }
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "INDEXED"

    # 5. GET /api/v1/memory/recall
    resp = client.get("/api/v1/memory/recall?query=reinforcement+learning+training")
    assert resp.status_code == 200
    recall_data = resp.json()
    assert recall_data["count"] >= 1
    assert recall_data["memories"][0]["memory_id"] == "mem_api_test_01"
