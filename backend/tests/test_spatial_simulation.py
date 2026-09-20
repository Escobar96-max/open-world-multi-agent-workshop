"""
Unit Tests for Antigravity Spatial Grid & DJ Frequency Node.
"""

import sys
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.spatial_engine import SpatialEngine
from app.services.dj_frequency import DJFrequencyNode
from app.services.vault_manager import VaultManager
from app.routers.spatial_router import router as spatial_router


def test_spatial_engine_zones_and_clamping(tmp_path):
    vault = VaultManager(vault_path=tmp_path / "vault")
    engine = SpatialEngine(vault_manager=vault)

    # Work Plaza
    zone, temp = engine.classify_zone(20.0, 30.0)
    assert zone == "Work Plaza"
    assert temp == 0.2

    # Frequency Lounge
    zone2, temp2 = engine.classify_zone(70.0, 80.0)
    assert zone2 == "Frequency Lounge"
    assert temp2 == 1.6

    # Clamping out-of-bounds
    assert engine.clamp(-10.0) == 0.0
    assert engine.clamp(150.0) == 100.0


def test_spatial_teleport_and_encounters(tmp_path):
    vault = VaultManager(vault_path=tmp_path / "vault")
    engine = SpatialEngine(vault_manager=vault)

    # Teleport Orion to Lounge
    res = engine.teleport("Orion_Prime", "lounge")
    assert res["success"] is True
    assert res["agent"]["x"] == 75.0
    assert res["agent"]["y"] == 75.0
    assert res["agent"]["zone"] == "Frequency Lounge"
    assert res["agent"]["temperature"] == 1.6

    # Teleport Nova close to Orion (distance <= 5.0)
    res2 = engine.update_position("Nova", 76.0, 76.0)
    assert res2["success"] is True

    encounters = engine.check_proximity()
    assert len(encounters) >= 1
    found = any(
        (e["agent_1"] == "Orion_Prime" and e["agent_2"] == "Nova") or
        (e["agent_1"] == "Nova" and e["agent_2"] == "Orion_Prime")
        for e in encounters
    )
    assert found is True


def test_dj_frequency_harmonics(tmp_path):
    vault = VaultManager(vault_path=tmp_path / "vault")
    dj = DJFrequencyNode(vault_manager=vault)

    # Default is 432Hz
    state = dj.get_state()
    assert state["frequency_hz"] == 432
    assert state["target_temperature"] == 1.6

    # Modulate to 528Hz
    res = dj.set_frequency(528)
    assert res["frequency_hz"] == 528

    # Verify log in World/lounge_logs.md
    lounge_log = tmp_path / "vault" / "World" / "lounge_logs.md"
    assert lounge_log.exists()
    assert "528Hz" in lounge_log.read_text(encoding="utf-8")


def test_spatial_router_endpoints():
    app = FastAPI()
    app.include_router(spatial_router)
    client = TestClient(app)

    # 1. State
    res = client.get("/api/v1/spatial/state")
    assert res.status_code == 200
    data = res.json()
    assert "grid" in data
    assert "agents" in data
    assert "frequency_state" in data

    # 2. Teleport
    tele_resp = client.post("/api/v1/spatial/teleport", json={"agent_id": "Sentinel_Alpha", "target": "plaza"})
    assert tele_resp.status_code == 200

    # 3. Tick
    tick_resp = client.post("/api/v1/spatial/tick")
    assert tick_resp.status_code == 200
    assert "tick" in tick_resp.json()

    # 4. Frequency
    freq_resp = client.post("/api/v1/spatial/frequency", json={"frequency": 40})
    assert freq_resp.status_code == 200
    assert freq_resp.json()["frequency_hz"] == 40
