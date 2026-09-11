import pytest
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

from gateway_server import app
from services.lounge_manager import LoungeManager
from services.vault_manager import VaultManager

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def temp_vault(tmp_path):
    vault_root = tmp_path / "test_lounge_vault"
    vm = VaultManager(vault_root=str(vault_root))
    vm.ensure_vault_hierarchy()
    yield vm
    if vault_root.exists():
        shutil.rmtree(vault_root, ignore_errors=True)

def test_lounge_manager_recording_and_retrieval(temp_vault):
    lm = LoungeManager(vault_manager=temp_vault)
    entry = lm.record_dialogue(
        speaker_id="Curator_Node",
        message="Observing harmonic resonance across the open grid.",
        frequency_hz=432,
        listener_id="Sentinel_Alpha",
        temperature=1.6
    )
    assert entry["speaker"] == "Curator_Node"
    assert entry["frequency_hz"] == 432
    assert "harmonic resonance" in entry["message"]

    # Verify retrieval
    logs = lm.get_recent_logs(limit=5)
    assert len(logs) >= 1
    assert "Curator_Node" in logs[0]["speaker"]

def test_spatial_api_endpoints(client):
    # 1. GET /api/v1/spatial/state
    res_state = client.get("/api/v1/spatial/state")
    assert res_state.status_code == 200
    data = res_state.json()
    assert "matrix_bounds" in data
    assert "agents" in data

    # 2. POST /api/v1/spatial/teleport (with admin key)
    res_tp = client.post("/api/v1/spatial/teleport", json={
        "agent_id": "Sentinel_Alpha",
        "x": 60.0,
        "y": 65.0,
        "admin_key": "op_secret_master_key_9921"
    })
    assert res_tp.status_code == 200
    assert "Frequency Lounge" in res_tp.json()["agent"]["zone"]

    # 3. POST /api/v1/spatial/step
    res_step = client.post("/api/v1/spatial/step")
    assert res_step.status_code == 200
    assert "active_agents" in res_step.json()

def test_frequency_and_lounge_api_endpoints(client):
    # 1. GET /api/v1/lounge/frequency
    res_freq = client.get("/api/v1/lounge/frequency")
    assert res_freq.status_code == 200
    assert "active_frequency_hz" in res_freq.json()

    # 2. POST /api/v1/lounge/frequency
    res_shift = client.post("/api/v1/lounge/frequency", json={
        "frequency_hz": 528,
        "reason": "Test Shift",
        "admin_key": "op_secret_master_key_9921"
    })
    assert res_shift.status_code == 200
    assert res_shift.json()["frequency_state"]["active_frequency_hz"] == 528

    # 3. POST /api/v1/lounge/dialogue
    res_diag = client.post("/api/v1/lounge/dialogue", json={
        "speaker_id": "Sentinel_Alpha",
        "message": "Testing real-time lounge transmission over HTTP.",
        "listener_id": "Curator_Node"
    })
    assert res_diag.status_code == 200

    # 4. GET /api/v1/lounge/logs
    res_logs = client.get("/api/v1/lounge/logs?limit=5")
    assert res_logs.status_code == 200
    assert res_logs.json()["count"] >= 1

def test_operator_web_command_deck_rendering(client):
    res_deck = client.get("/api/v1/console/deck")
    assert res_deck.status_code == 200
    assert "text/html" in res_deck.headers["content-type"]
    html = res_deck.text
    assert "OPERATOR C2 COMMAND DECK" in html or "AGENT WORLD C2 DECK" in html
    assert "spatialCanvas" in html
    assert "DJ FREQUENCY" in html
    assert "toggleWebAudioTone" in html

def test_gateway_status_reflects_phase_2(client):
    res_status = client.get("/api/v1/status")
    assert res_status.status_code == 200
    status = res_status.json()
    assert "Phase 3" in status["phase"]
    assert "dj_frequency" in status
