import pytest
from fastapi.testclient import TestClient
from gateway_server import app

client = TestClient(app)
ADMIN_KEY = "op_secret_master_key_9921"

def test_unified_deck_html_contains_open_world_and_c2():
    """Verify that GET /api/v1/console/deck contains both C2 and Open World features."""
    res = client.get("/api/v1/console/deck")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    html = res.text

    # Verify Unified Branding
    assert "OPERATOR C2 COMMAND DECK" in html
    assert "AUTONOMOUS OPEN WORLD" in html

    # Verify Canvas & DJ Synthesizer
    assert "spatialCanvas" in html
    assert "DJ FREQUENCY" in html
    assert "toggleWebAudioTone" in html
    assert "shiftFrequency" in html

    # Verify Open World Physics & Weather Controls
    assert "0.0g Float" in html
    assert "1.0g Earth" in html
    assert "-1.2g Singularity" in html
    assert "setGravity" in html
    assert "setWeather" in html
    assert "triggerSingularityAnomaly" in html

    # Verify Cognitive Dual-Buffer Memory Vault
    assert "Dual-Buffer Memory Vault" in html
    assert "HOT BUFFER" in html
    assert "COLD VAULT" in html
    assert "TOMBSTONES" in html
    assert "triggerMemoryConsolidation" in html
    assert "recoverMemoryFile" in html

def test_open_world_simulation_endpoints_on_gateway():
    """Verify simulation endpoints /api/state, /api/step, /api/gravity, /api/weather."""
    # 1. State
    res_state = client.get("/api/state")
    assert res_state.status_code == 200
    data = res_state.json()
    assert "tick_count" in data or "tick" in data

    # 2. Gravity
    res_g = client.post("/api/gravity", json={"gravity": "0.4g"})
    assert res_g.status_code == 200
    assert res_g.json().get("gravity") == "0.4g" or res_g.json().get("gravity_numeric") == 0.4

    # 3. Weather
    res_w = client.post("/api/weather", json={"condition": "rain"})
    assert res_w.status_code == 200
    assert res_w.json().get("weather", {}).get("condition") == "rain"

    # 4. Step
    res_step = client.post("/api/step")
    assert res_step.status_code == 200

    # 5. Anomaly
    res_anom = client.post("/api/anomaly")
    assert res_anom.status_code == 200

    # 6. Reset
    res_reset = client.post("/api/reset")
    assert res_reset.status_code == 200

def test_memory_vault_endpoints_on_gateway():
    """Verify memory consolidation endpoints on gateway_server."""
    res_stats = client.get("/api/memory/stats")
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert "hot_count" in stats
    assert "cold_count" in stats
    assert "tombstone_count" in stats

    res_cons = client.post("/api/memory/consolidate")
    assert res_cons.status_code == 200

def test_c2_extended_slash_commands():
    """Verify C2 dispatcher handles extended /gravity, /weather, /freq, /step."""
    # /gravity
    res_g = client.post(
        "/api/v1/console/command",
        headers={"X-Admin-Key": ADMIN_KEY},
        json={"command": "/gravity 0.0g"}
    )
    assert res_g.status_code == 200
    assert res_g.json()["status"] == "SUCCESS"
    assert res_g.json()["command"] == "/gravity"

    # /weather
    res_w = client.post(
        "/api/v1/console/command",
        headers={"X-Admin-Key": ADMIN_KEY},
        json={"command": "/weather storm"}
    )
    assert res_w.status_code == 200
    assert res_w.json()["status"] == "SUCCESS"
    assert res_w.json()["command"] == "/weather"

    # /freq
    res_f = client.post(
        "/api/v1/console/command",
        headers={"X-Admin-Key": ADMIN_KEY},
        json={"command": "/freq 528"}
    )
    assert res_f.status_code == 200
    assert res_f.json()["status"] == "SUCCESS"
    assert res_f.json()["command"] == "/freq"

    # /step
    res_s = client.post(
        "/api/v1/console/command",
        headers={"X-Admin-Key": ADMIN_KEY},
        json={"command": "/step"}
    )
    assert res_s.status_code == 200
    assert res_s.json()["status"] == "SUCCESS"
