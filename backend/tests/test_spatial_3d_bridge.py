import sys
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.spatial_engine import SpatialEngine
from app.routers.spatial_router import router as spatial_router, get_spatial_engine

@pytest.fixture
def app():
    test_app = FastAPI()
    test_app.include_router(spatial_router)
    return test_app

@pytest.fixture
def client(app):
    return TestClient(app)

def test_compile_live_3d_state_structure():
    engine = get_spatial_engine()
    data = engine.compile_live_3d_state()

    assert data["type"] == "LIVE_3D_TELEMETRY"
    assert "tick" in data
    assert "world_harmonics" in data
    assert data["world_harmonics"] == 432.04

    # Check entities
    entities = {e["id"]: e for e in data["entities"]}
    assert "Bob" in entities
    assert "Alice" in entities
    assert "Dr_Aris" in entities
    assert "AEGIS_Core" in entities
    assert "Architect_Prime" in entities
    assert "DJ_Frequency" in entities
    assert "Sentinel_Alpha" in entities
    assert "Laila" in entities

    # Check 3D position structure
    bob = entities["Bob"]
    assert "position" in bob
    assert "x" in bob["position"]
    assert "y" in bob["position"]
    assert "z" in bob["position"]
    assert bob["recent_speech"] is not None

    # Check spires
    spires = data["spires"]
    assert "quantum_singularity" in spires
    assert "gatekeeper_pow" in spires
    assert "neural_matrix" in spires
    assert "frequency_sanctum" in spires

def test_rest_live_3d_endpoint(client):
    res = client.get("/api/v1/spatial/live-3d")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "LIVE_3D_TELEMETRY"
    assert len(data["entities"]) >= 10

def test_websocket_3d_live_stream(client):
    with client.websocket_connect("/api/v1/spatial/ws/live-3d") as ws:
        # First message is the initial snapshot
        init_data = ws.receive_json()
        assert init_data["type"] == "LIVE_3D_TELEMETRY"
        assert len(init_data["entities"]) >= 10

        # Send ping
        ws.send_text("ping")
        resp = ws.receive_text()
        assert resp == "pong"
