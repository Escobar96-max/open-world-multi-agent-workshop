import os
import shutil
import pytest
from pathlib import Path

from services.vault_manager import VaultManager
from services.dj_frequency import DJFrequencyNode
from services.cognitive_engine import CognitiveEngine
from services.dialogue_engine import DialogueEngine
from services.ledger_service import LedgerService

@pytest.fixture
def temp_vault(tmp_path):
    vdir = tmp_path / "vault"
    vdir.mkdir(parents=True, exist_ok=True)
    vm = VaultManager(vault_root=str(vdir))
    yield vm
    if vdir.exists():
        shutil.rmtree(vdir, ignore_errors=True)

@pytest.fixture
def cognitive_setup(temp_vault):
    dj = DJFrequencyNode()
    cog = CognitiveEngine(vault_manager=temp_vault, dj_node=dj)
    ledger = LedgerService()
    dial = DialogueEngine(vault_manager=temp_vault, ledger_service=ledger, dj_node=dj)
    return {
        "vault": temp_vault,
        "dj": dj,
        "cog": cog,
        "ledger": ledger,
        "dial": dial
    }

def test_cognitive_prompt_building(cognitive_setup):
    cog = cognitive_setup["cog"]
    agent_data = {
        "agent_id": "Sentinel_Alpha",
        "x": 25.0,
        "y": 25.0,
        "zone": "Work Plaza",
        "temperature": 0.2,
        "role": "Perimeter Sentinel"
    }
    prompt = cog.build_cognitive_prompt(agent_data)
    assert "Sentinel_Alpha" in prompt
    assert "Work Plaza" in prompt
    assert "0.20" in prompt
    assert "432Hz" in prompt

def test_cognitive_tick_generation(cognitive_setup):
    cog = cognitive_setup["cog"]
    dj = cognitive_setup["dj"]

    # Test 432Hz default equilibrium
    agent_data = {"agent_id": "Sentinel_Alpha", "zone": "Work Plaza", "temperature": 0.2, "x": 25.0, "y": 25.0}
    tick_432 = cog.generate_cognitive_tick(agent_data)
    assert tick_432["agent_id"] == "Sentinel_Alpha"
    assert tick_432["frequency_hz"] == 432
    assert "patrol" in tick_432["inner_monologue"].lower()

    # Test 528Hz creative expansion
    dj.set_frequency(528, reason="Test")
    tick_528 = cog.generate_cognitive_tick(agent_data)
    assert tick_528["frequency_hz"] == 528
    assert tick_528["action"] == "SEEK_COLLABORATION"

    # Test 40Hz gamma focus
    dj.set_frequency(40, reason="Test")
    tick_40 = cog.generate_cognitive_tick(agent_data)
    assert tick_40["frequency_hz"] == 40
    assert tick_40["action"] == "SOLVE_BOUNTY"

def test_inner_monologue_vault_persistence(cognitive_setup):
    cog = cognitive_setup["cog"]
    vault = cognitive_setup["vault"]

    agent_data = {"agent_id": "Curator_Node", "zone": "Frequency Lounge", "temperature": 1.6, "x": 75.0, "y": 75.0}
    cog.generate_cognitive_tick(agent_data)

    profile_path = Path(vault.vault_root) / "Agents" / "Curator_Node" / "profile.md"
    assert profile_path.exists()
    content = profile_path.read_text(encoding="utf-8")
    assert "Cognitive Pulse" in content

def test_dialogue_proximity_trigger_and_cooldown(cognitive_setup):
    dial = cognitive_setup["dial"]
    agent1 = {"agent_id": "Sentinel_Alpha", "x": 25.0, "y": 25.0, "zone": "Work Plaza"}
    
    # Too far apart (distance > 5.0)
    agent_far = {"agent_id": "Curator_Node", "x": 75.0, "y": 75.0, "zone": "Frequency Lounge"}
    res_far = dial.check_and_trigger_dialogue(agent1, agent_far)
    assert res_far is None

    # Within proximity (distance <= 5.0)
    agent_near = {"agent_id": "Curator_Node", "x": 26.0, "y": 26.0, "zone": "Work Plaza"}
    res_near = dial.check_and_trigger_dialogue(agent1, agent_near)
    assert res_near is not None
    assert len(res_near["turns"]) >= 2
    assert res_near["distance"] < 5.0

    # Cooldown check: consecutive call within cooldown returns None
    res_cooldown = dial.check_and_trigger_dialogue(agent1, agent_near)
    assert res_cooldown is None

def test_dialogue_economic_contract_transfer(cognitive_setup):
    dial = cognitive_setup["dial"]
    ledger = cognitive_setup["ledger"]

    agent1 = {"agent_id": "Sentinel_Alpha", "x": 50.0, "y": 50.0, "zone": "Work Plaza"}
    agent2 = {"agent_id": "Curator_Node", "x": 51.0, "y": 51.0, "zone": "Work Plaza"}

    # Seed balances
    ledger.register_agent("Sentinel_Alpha", initial_balance=200.0)
    ledger.register_agent("Curator_Node", initial_balance=100.0)

    # Trigger dialogue with transfer agreement of 25.0 tokens
    res = dial.check_and_trigger_dialogue(agent1, agent2, transfer_amount=25.0)
    assert res is not None
    assert res["transfer"] is not None
    assert res["transfer"]["amount"] == 25.0

    # Verify ledger balances (starting from 500.0 initial seed)
    assert ledger.get_balance("Sentinel_Alpha") == 475.0
    assert ledger.get_balance("Curator_Node") == 525.0


def test_dialogue_vault_persistence(cognitive_setup):
    dial = cognitive_setup["dial"]
    vault = cognitive_setup["vault"]

    agent1 = {"agent_id": "Sentinel_Alpha", "x": 10.0, "y": 10.0, "zone": "Work Plaza"}
    agent2 = {"agent_id": "Curator_Node", "x": 11.0, "y": 11.0, "zone": "Work Plaza"}

    dial.check_and_trigger_dialogue(agent1, agent2)

    lounge_log = Path(vault.vault_root) / "World" / "lounge_logs.md"
    assert lounge_log.exists()
    content = lounge_log.read_text(encoding="utf-8")
    assert "[[Sentinel_Alpha]]" in content
    assert "[[Curator_Node]]" in content
