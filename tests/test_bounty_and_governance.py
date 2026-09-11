import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from services.vault_manager import VaultManager
from services.ledger_service import LedgerService
from services.bounty_manager import BountyManager, BountyError
from services.governance_engine import GovernanceEngine, GovernanceError
from api.bounty_router import router as bounty_router
from api.governance_router import router as governance_router

app = FastAPI()
app.include_router(bounty_router)
app.include_router(governance_router)
client = TestClient(app)

@pytest.fixture
def temp_env(tmp_path):
    vm = VaultManager(vault_root=str(tmp_path))
    vm.ensure_vault_hierarchy()
    ledger = LedgerService()
    # Seed agent balances
    ledger.register_agent("Sentinel_Alpha", initial_balance=500.0)
    ledger.register_agent("Curator_Node", initial_balance=500.0)
    ledger.register_agent("Architect_Prime", initial_balance=1000.0)
    ledger.register_agent("Voter_One", initial_balance=100.0)
    ledger.register_agent("Voter_Two", initial_balance=100.0)
    ledger.register_agent("Voter_Three", initial_balance=100.0)

    bounty_mgr = BountyManager(vault_manager=vm, ledger_service=ledger)
    gov_engine = GovernanceEngine(vault_manager=vm)
    return {
        "vm": vm,
        "ledger": ledger,
        "bounty_mgr": bounty_mgr,
        "gov_engine": gov_engine
    }

def test_bounty_lifecycle_and_escrow_settlement(temp_env):
    bm = temp_env["bounty_mgr"]
    ledger = temp_env["ledger"]
    vm = temp_env["vm"]

    # 1. Create bounty by Sentinel_Alpha (500 TK)
    bounty = bm.create_bounty(
        title="Perimeter Breach Analysis",
        description="Inspect perimeter telemetry around Work Plaza",
        reward=150.0,
        posted_by="Sentinel_Alpha"
    )
    b_id = bounty["bounty_id"]
    assert bounty["status"] == "OPEN"
    assert bounty["reward"] == 150.0

    # 2. Prevent poster from claiming own bounty
    with pytest.raises(BountyError):
        bm.claim_bounty(b_id, "Sentinel_Alpha")

    # 3. Curator_Node claims bounty
    claimed = bm.claim_bounty(b_id, "Curator_Node")
    assert claimed["status"] == "CLAIMED"
    assert claimed["assignee"] == "Curator_Node"

    # 4. Submit proof of work
    submitted = bm.submit_bounty_work(b_id, "Curator_Node", "Telemetry logs clean: 0 breaches detected.")
    assert submitted["status"] == "SUBMITTED"

    # 5. Complete bounty -> Release payment
    res = bm.complete_bounty(b_id, verifier_id="Sentinel_Alpha")
    assert res["status"] == "COMPLETED"
    assert res["bounty"]["status"] == "COMPLETED"

    # Verify balance settlement in Ledger: Sentinel paid 150, Curator received 150
    assert ledger.get_balance("Sentinel_Alpha") == 350.0
    assert ledger.get_balance("Curator_Node") == 650.0

    # Verify bounty board markdown saved in vault
    board_file = vm.world_path / "bounty_board.md"
    assert board_file.is_file()
    fm, body = vm.read_file(board_file)
    assert fm["total_bounties"] >= 1

def test_bounty_insufficient_funds_rejection(temp_env):
    bm = temp_env["bounty_mgr"]
    with pytest.raises(BountyError):
        # Sentinel_Alpha only has 500 TK, cannot create 9999 TK bounty
        bm.create_bounty("Impossible Bounty", "Too expensive", reward=9999.0, posted_by="Sentinel_Alpha")

def test_governance_consensus_and_enactment(temp_env):
    gov = temp_env["gov_engine"]
    vm = temp_env["vm"]

    # 1. Propose RFC
    prop = gov.submit_proposal(
        title="RFC-002: Spatial Physics Low Gravity Sunday",
        summary="Adjust gravity constant from 1.0g to 0.4g every Sunday for lounge floating.",
        proposer_id="Sentinel_Alpha",
        directives="Set sim_engine gravity to 0.4g on Sundays."
    )
    p_id = prop["proposal_id"]
    assert prop["status"] == "ACTIVE"

    # 2. First vote FOR (Sentinel_Alpha)
    v1 = gov.cast_vote(p_id, "Sentinel_Alpha", "FOR")
    assert v1["current_status"] == "ACTIVE"
    assert v1["votes_for"] == 1

    # Double voting rejection
    with pytest.raises(GovernanceError):
        gov.cast_vote(p_id, "Sentinel_Alpha", "FOR")

    # 3. Second vote FOR (Curator_Node) -> 2/2 = 100% >= 75%, quorum = 2 -> PASSED!
    v2 = gov.cast_vote(p_id, "Curator_Node", "FOR")
    assert v2["current_status"] == "PASSED"
    assert v2["enacted"] is True

    # Check that enactment was recorded in vault/World/state.md
    state_file = vm.world_path / "state.md"
    assert state_file.is_file()
    _, body = vm.read_file(state_file)
    assert "RFC-002: Spatial Physics Low Gravity Sunday" in body

def test_bounty_and_governance_api(temp_env, monkeypatch):
    from api import bounty_router as br
    from api import governance_router as gr

    monkeypatch.setattr(br, "bounty_mgr", temp_env["bounty_mgr"])
    monkeypatch.setattr(gr, "governance_engine", temp_env["gov_engine"])

    # 1. GET /api/v1/bounty/list
    resp = client.get("/api/v1/bounty/list")
    assert resp.status_code == 200
    assert "bounties" in resp.json()

    # 2. POST /api/v1/bounty/create
    resp = client.post(
        "/api/v1/bounty/create",
        json={
            "title": "API Test Bounty",
            "description": "Integration check",
            "reward": 50.0,
            "posted_by": "Curator_Node"
        }
    )
    assert resp.status_code == 200
    b_id = resp.json()["bounty_id"]

    # 3. POST /api/v1/bounty/claim
    resp = client.post("/api/v1/bounty/claim", json={"bounty_id": b_id, "agent_id": "Sentinel_Alpha"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "CLAIMED"

    # 4. GET /api/v1/governance/proposals
    resp = client.get("/api/v1/governance/proposals")
    assert resp.status_code == 200
    assert "proposals" in resp.json()

    # 5. POST /api/v1/governance/propose
    resp = client.post(
        "/api/v1/governance/propose",
        json={
            "title": "API RFC Proposal",
            "summary": "Check API governance voting",
            "proposer_id": "Curator_Node",
            "directives": "Execute test protocol"
        }
    )
    assert resp.status_code == 200
    prop_id = resp.json()["proposal_id"]

    # 6. POST /api/v1/governance/vote
    resp = client.post(
        "/api/v1/governance/vote",
        json={
            "proposal_id": prop_id,
            "agent_id": "Curator_Node",
            "choice": "FOR"
        }
    )
    assert resp.status_code == 200
    assert resp.json()["votes_for"] == 1
