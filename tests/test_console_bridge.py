import pytest
import os
from fastapi.testclient import TestClient
from gateway_server import app
from services.vault_manager import VaultManager

client = TestClient(app)
ADMIN_KEY = os.getenv("ADMIN_SECRET_KEY", "op_secret_master_key_9921")
vault_mgr = VaultManager()

def test_unauthorized_console_command_rejected():
    """Test that requests missing or with invalid ADMIN_SECRET_KEY return 401."""
    res = client.post("/api/v1/console/command", json={
        "command": "/teleport Sentinel_Alpha 20 20"
    })
    assert res.status_code == 401

    res_invalid = client.post(
        "/api/v1/console/command",
        headers={"X-Admin-Key": "wrong_key_123"},
        json={"command": "/teleport Sentinel_Alpha 20 20"}
    )
    assert res_invalid.status_code == 401

def test_teleport_slash_command_execution():
    """Test /teleport slash command updates coordinates and triggers zone shift."""
    target_agent = "Sentinel_Alpha"
    
    # Teleport to Frequency Lounge (coords > 50)
    res = client.post(
        "/api/v1/console/command",
        headers={"X-Admin-Key": ADMIN_KEY},
        json={"command": f"/teleport {target_agent} 65.5 75.0"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["new_coordinates"] == [65.5, 75.0]
    assert data["zone"] == "Frequency Lounge & Sanctum"
    assert data["temperature"] == 1.6

    # Verify profile file was updated on disk
    fm, body = vault_mgr.get_agent_profile(target_agent)
    assert fm["coordinates"] == [65.5, 75.0]
    assert fm["zone"] == "Frequency Lounge & Sanctum"

def test_train_slash_command_execution():
    """Test /train slash command assigns curriculum and logs memory."""
    target_agent = "Curator_Node"
    curriculum = "Python AST & Graph Traversal Optimizations"

    res = client.post(
        "/api/v1/console/command",
        headers={"X-Admin-Key": ADMIN_KEY},
        json={"command": f"/train {target_agent} {curriculum}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["command"] == "/train"
    assert data["curriculum"] == curriculum

def test_natural_language_directive_priority_10_injection():
    """
    Test that natural language directives without a slash command are treated as Priority 10
    directives and injected into the agent's memory stream.
    """
    target_agent = "Sentinel_Alpha"
    directive = "Elevate perimeter vigilance and immediately log all unverified network beacons."

    res = client.post(
        "/api/v1/console/command",
        headers={"X-Admin-Key": ADMIN_KEY},
        json={
            "command": directive,
            "target_agent": target_agent
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["type"] == "NATURAL_LANGUAGE_DIRECTIVE"
    assert data["importance"] == 10
    assert data["agent_id"] == target_agent
    
    # Verify file physically exists in /vault/Agents/{agent_id}/memories/
    mem_file_path = data["memory_file"]
    fm, body = vault_mgr.read_file(vault_mgr.vault_path / "Agents" / target_agent / "memories" / f"{data['memory_id']}.md")
    assert fm["importance"] == 10
    assert "OPERATOR DIRECTIVE" in body
    assert directive in body

def test_console_deck_html_mount():
    """Test that the web command deck UI is accessible on GET /api/v1/console/deck."""
    res = client.get("/api/v1/console/deck")
    assert res.status_code == 200
    assert "OPERATOR C2 COMMAND DECK" in res.text
    assert "X-Admin-Key" in res.text or "ADMIN SECRET KEY" in res.text
