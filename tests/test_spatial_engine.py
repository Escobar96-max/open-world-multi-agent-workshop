import pytest
import math
import shutil
from pathlib import Path
from services.spatial_engine import SpatialEngine
from services.vault_manager import VaultManager

@pytest.fixture
def temp_vault(tmp_path):
    vault_root = tmp_path / "test_vault"
    vm = VaultManager(vault_root=str(vault_root))
    vm.ensure_vault_hierarchy()
    yield vm
    if vault_root.exists():
        shutil.rmtree(vault_root, ignore_errors=True)

def test_spatial_engine_init_and_seeding(temp_vault):
    engine = SpatialEngine(vault_manager=temp_vault)
    state = engine.get_state()
    assert state["agent_count"] >= 2
    assert "Sentinel_Alpha" in engine.agents
    assert "Curator_Node" in engine.agents
    assert engine.agents["Sentinel_Alpha"]["zone"] == "Work Plaza"
    assert engine.agents["Sentinel_Alpha"]["temperature"] == 0.2
    assert engine.agents["Curator_Node"]["zone"] == "Frequency Lounge & Sanctum"
    assert engine.agents["Curator_Node"]["temperature"] == 1.6

def test_zone_and_temperature_classification(temp_vault):
    engine = SpatialEngine(vault_manager=temp_vault)
    # Work Plaza bounds: 0 <= x <= 50 and 0 <= y <= 50
    zone1, temp1 = engine.get_zone_and_temp(10.0, 45.0)
    assert zone1 == "Work Plaza"
    assert temp1 == 0.2

    # Frequency Lounge & Sanctum: x > 50 or y > 50
    zone2, temp2 = engine.get_zone_and_temp(55.0, 20.0)
    assert zone2 == "Frequency Lounge & Sanctum"
    assert temp2 == 1.6

    zone3, temp3 = engine.get_zone_and_temp(80.0, 80.0)
    assert zone3 == "Frequency Lounge & Sanctum"
    assert temp3 == 1.6

def test_teleport_agent_success_and_bounds_enforcement(temp_vault):
    engine = SpatialEngine(vault_manager=temp_vault)
    # Teleport to valid Lounge coordinates
    res = engine.teleport_agent("Sentinel_Alpha", 85.0, 90.0)
    assert res["x"] == 85.0
    assert res["y"] == 90.0
    assert res["zone"] == "Frequency Lounge & Sanctum"
    assert res["temperature"] == 1.6

    # Verify updated Obsidian profile
    fm, _ = temp_vault.get_agent_profile("Sentinel_Alpha")
    assert fm["coordinates"] == [85.0, 90.0]
    assert fm["zone"] == "Frequency Lounge & Sanctum"

    # Out of bounds should raise ValueError
    with pytest.raises(ValueError):
        engine.teleport_agent("Sentinel_Alpha", 105.0, 50.0)
    with pytest.raises(ValueError):
        engine.teleport_agent("Sentinel_Alpha", -5.0, 50.0)

def test_proximity_encounter_detection_and_debouncing(temp_vault):
    engine = SpatialEngine(vault_manager=temp_vault)
    # Move both agents close together: distance = 3.0 (< 5.0 units)
    engine.teleport_agent("Sentinel_Alpha", 20.0, 20.0)
    engine.teleport_agent("Curator_Node", 20.0, 23.0)

    # Step simulation
    step_data = engine.step_simulation(delta_time=0.0)
    encounters = step_data["encounters"]
    assert len(encounters) == 1
    assert encounters[0]["distance"] == 3.0

    # Verify bidirectional memory in Obsidian
    mems_a = temp_vault.list_agent_memories("Sentinel_Alpha")
    mems_b = temp_vault.list_agent_memories("Curator_Node")
    assert any("Curator_Node" in m["filename"] or "encounter" in m["tags"] for m in mems_a)
    assert any("Sentinel_Alpha" in m["filename"] or "encounter" in m["tags"] for m in mems_b)

    # Next immediate step within cooldown should NOT create duplicate memory files
    initial_count_a = len(mems_a)
    engine.step_simulation(delta_time=0.0)
    mems_a_after = temp_vault.list_agent_memories("Sentinel_Alpha")
    assert len(mems_a_after) == initial_count_a
