"""
Test Suite: World Inspector & Autonomous Open World Integration
Verifies that:
1. WorldInspector dynamically compiles live spatial positions, frequency states, and vault memories.
2. SpatialEngine persists live coordinates to vault/World/state.md and logs encounter dialogues.
3. Orion Prime and Nova inject live world telemetry and answer world queries dynamically
   without static canned fallback templates.
"""

import sys
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.world_inspector import WorldInspector, get_world_inspector
from app.services.spatial_engine import SpatialEngine, SpatialAgent
from app.services.executive_duo import ExecutiveDuo, is_world_query
from app.services.vault_manager import VaultManager


@pytest.fixture
def test_vault(tmp_path):
    vault = VaultManager(vault_path=str(tmp_path / "vault"))
    # Seed state.md and lounge_logs.md
    state_file = vault.world_dir / "state.md"
    state_file.write_text("# Initial State", encoding="utf-8")
    lounge_file = vault.world_dir / "lounge_logs.md"
    lounge_file.write_text("- `[2026-09-24 00:00:00 UTC]` **DJ_Frequency**: 432Hz stream verified.\n", encoding="utf-8")
    
    # Seed an agent memory for Architect_Prime
    arch_mem = vault.agents_dir / "Architect_Prime" / "memories"
    arch_mem.mkdir(parents=True, exist_ok=True)
    (arch_mem / "20260924_test_memory.md").write_text(
        "---\ntitle: 'AST Pipeline Verified'\n---\n## Observation\nArchitect Prime completed AST refactor.\n",
        encoding="utf-8"
    )
    return vault


def test_world_inspector_telemetry(test_vault):
    inspector = WorldInspector(vault_path=test_vault.vault_path)
    telemetry = inspector.get_live_world_telemetry()

    assert "spatial_agents" in telemetry
    assert "Architect_Prime" in telemetry["spatial_agents"]
    assert "recent_lounge_talks" in telemetry
    assert "DJ_Frequency" in telemetry["recent_lounge_talks"]
    assert "agent_activities" in telemetry
    assert "Architect_Prime" in telemetry["agent_activities"]
    assert telemetry["agent_activities"]["Architect_Prime"]["title"] == "AST Pipeline Verified"

    prompt_block = inspector.format_telemetry_prompt_block(telemetry)
    assert "=== LIVE AGENT WORLD TELEMETRY (REAL TIME) ===" in prompt_block
    assert "@Architect_Prime" in prompt_block
    assert "AST Pipeline Verified" in prompt_block


def test_spatial_engine_sync_and_dispatch(test_vault):
    engine = SpatialEngine(vault_manager=test_vault)
    
    # 1. State sync to vault
    engine.sync_state_to_vault()
    state_file = test_vault.world_dir / "state.md"
    assert state_file.exists()
    content = state_file.read_text(encoding="utf-8")
    assert "Antigravity Spatial World: Live System State" in content
    assert "Architect_Prime" in content
    assert "Coordinates" in content

    # 2. Dispatch agent
    res = engine.dispatch_agent_to_zone("Architect_Prime", "work_plaza", "Core Compilation")
    assert res["success"] is True
    agent = engine.agents["Architect_Prime"]
    assert agent.zone == "Work Plaza"
    assert "Core Compilation" in agent.status

    # 3. Check dispatch log in lounge_logs.md
    lounge_text = (test_vault.world_dir / "lounge_logs.md").read_text(encoding="utf-8")
    assert "Executive Dispatch" in lounge_text or "Core Compilation" in lounge_text


def test_spatial_engine_encounter_dialogue(test_vault):
    engine = SpatialEngine(vault_manager=test_vault)
    
    # Place Orion Prime and Architect Prime in close proximity
    engine.update_position("Orion_Prime", 20.0, 20.0)
    engine.update_position("Architect_Prime", 21.0, 21.0)
    
    encounters = engine.check_proximity()
    assert len(encounters) >= 1
    
    # Verify dialogue was logged
    lounge_text = (test_vault.world_dir / "lounge_logs.md").read_text(encoding="utf-8")
    assert "Spatial_Encounter" in lounge_text
    assert "Orion Prime" in lounge_text or "Architect Prime" in lounge_text


def test_is_world_query_detection():
    # Bangla / Banglish queries
    assert is_world_query("world environment er update ki?") is True
    assert is_world_query("agents der ki obostha?") is True
    assert is_world_query("okhane agents der ki obostha ? tader world er vetore environment er updates ki?") is True
    assert is_world_query("frequency lounge er ki obostha") is True
    assert is_world_query("open world e ora kemon ache") is True
    
    # Unrelated queries
    assert is_world_query("scrape this website: https://example.com") is False
    assert is_world_query("valovasi Nova") is False


@pytest.mark.asyncio
async def test_executive_duo_dynamic_world_responses(test_vault):
    hub = ExecutiveDuo(vault_manager=test_vault, ollama_enabled=False)
    
    # 1. World query to Duo
    prompt = "okhane agents der ki obostha ? tader world er vetore environment er updates ki?"
    res = await hub.process_directive(prompt, operator="Boss")
    
    orion_resp = res.get("orion_response", "")
    nova_resp = res.get("nova_response", "")

    # Assert static canned strings are absent
    canned_string = "Shob check maaf koto update ki?"
    assert canned_string not in orion_resp
    assert canned_string not in nova_resp
    assert "Ambient_frequency 432, total_agents 6, active_zone Work Plaza & Frequency Lounge" not in orion_resp

    # Assert real dynamic data is present
    assert "Architect_Prime" in orion_resp
    assert "DJ_Frequency" in orion_resp
    assert "Work Plaza" in orion_resp or "Coordinates" in orion_resp
    assert "Architect_Prime" in nova_resp
    assert "UwU" in nova_resp
