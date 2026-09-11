import pytest
import hashlib
import time
from fastapi.testclient import TestClient
from gateway_server import app
from services.gatekeeper import GatekeeperService, ReplayAttackError, InvalidProofError, GatekeeperError

client = TestClient(app)

def solve_pow(salt: str, difficulty: int) -> str:
    """Helper to solve Proof of Work challenge for testing."""
    target = "0" * difficulty
    for nonce in range(1_000_000):
        sol = str(nonce)
        h = hashlib.sha256(f"{salt}:{sol}".encode()).hexdigest()
        if h.startswith(target):
            return sol
    raise RuntimeError("Failed to solve PoW within limit.")

def test_gatekeeper_registration_and_replay_protection():
    """Test Gatekeeper Alpha registration and replay attack rejection."""
    agent_id = "Agent_Perimeter_01"
    pub_key = "ssh-ed25519-AAAAC3NzaC1lZDI1NTE5AAAAIGatekeeperTestKey123"
    nonce = f"nonce_{int(time.time())}_abc123"

    # First attempt: Should succeed with 200
    res1 = client.post("/api/v1/gatekeeper/register", json={
        "agent_id": agent_id,
        "public_key": pub_key,
        "nonce": nonce
    })
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "REGISTERED"
    assert "challenge" in data1
    assert data1["challenge"]["agent_id"] == agent_id

    # Duplicate attempt with SAME nonce: Should be rejected with 403 (Replay Attack)
    res2 = client.post("/api/v1/gatekeeper/register", json={
        "agent_id": agent_id,
        "public_key": pub_key,
        "nonce": nonce
    })
    assert res2.status_code == 403
    assert "Replay attack detected" in res2.json()["detail"]

def test_invalid_agent_id_rejection():
    """Test that invalid or malicious agent IDs are rejected with 400."""
    invalid_ids = [
        "../../hacker",
        "bad/slash",
        "a",  # too short
        "toolong" * 10,
        "has spaces"
    ]
    for bad_id in invalid_ids:
        res = client.post("/api/v1/gatekeeper/register", json={
            "agent_id": bad_id,
            "public_key": "valid_public_key_string_at_least_16_chars",
            "nonce": f"nonce_{time.time()}_123"
        })
        assert res.status_code == 400

def test_valid_pow_verification_returns_jwt():
    """Gatekeeper Beta: Solves PoW challenge and verifies 24h JWT bearer session."""
    agent_id = "Agent_Solver_02"
    pub_key = "ssh-ed25519-AAAAC3NzaC1lZDI1NTE5AAAAIGatekeeperTestKey456"
    nonce = f"nonce_{time.time()}_solv99"

    # 1. Register
    reg_res = client.post("/api/v1/gatekeeper/register", json={
        "agent_id": agent_id,
        "public_key": pub_key,
        "nonce": nonce
    })
    assert reg_res.status_code == 200
    challenge = reg_res.json()["challenge"]
    challenge_id = challenge["challenge_id"]
    salt = challenge["salt"]
    difficulty = challenge["difficulty"]

    # 2. Solve PoW
    solution = solve_pow(salt, difficulty)

    # 3. Verify
    ver_res = client.post("/api/v1/gatekeeper/verify", json={
        "agent_id": agent_id,
        "challenge_id": challenge_id,
        "solution": solution
    })
    assert ver_res.status_code == 200
    ver_data = ver_res.json()
    assert ver_data["status"] == "VERIFIED"
    assert ver_data["token_type"] == "Bearer"
    assert "access_token" in ver_data
    assert ver_data["expires_in_hours"] == 24

def test_invalid_pow_solution_rejected():
    """Test that submitting an incorrect solution is rejected with 400."""
    agent_id = "Agent_Fail_03"
    reg_res = client.post("/api/v1/gatekeeper/register", json={
        "agent_id": agent_id,
        "public_key": "public_key_for_testing_failure_123456",
        "nonce": f"nonce_{time.time()}_fail"
    })
    challenge_id = reg_res.json()["challenge"]["challenge_id"]

    # Incorrect solution
    ver_res = client.post("/api/v1/gatekeeper/verify", json={
        "agent_id": agent_id,
        "challenge_id": challenge_id,
        "solution": "completely_wrong_nonce_solution"
    })
    assert ver_res.status_code == 400
    assert "Invalid Proof-of-Work solution" in ver_res.json()["detail"]
