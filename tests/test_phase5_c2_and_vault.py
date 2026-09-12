import os
import shutil
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from gateway_server import app
from services.vault_manager import VaultManager
from services.dev_loop import DevLoopEngine
from services.daily_briefing import DailyBriefingEngine
from services.bot_bridge import TelegramBotBridge
from services.dj_frequency import DJFrequencyNode

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def temp_vault(tmp_path):
    vdir = tmp_path / "vault"
    vdir.mkdir(parents=True, exist_ok=True)
    vm = VaultManager(vault_root=str(vdir))
    yield vm
    if vdir.exists():
        shutil.rmtree(vdir, ignore_errors=True)

def test_console_agent_consciousness_endpoint(client):
    res = client.get("/api/v1/console/agent/Sentinel_Alpha/consciousness")
    assert res.status_code == 200
    data = res.json()
    assert data["agent_id"] == "Sentinel_Alpha"
    assert "spatial" in data
    assert "cognitive" in data
    assert "balance" in data
    assert "inner_monologue" in data["cognitive"]

def test_devloop_autonomous_feature_synthesis(temp_vault):
    dev = DevLoopEngine(vault_manager=temp_vault)
    # Validate baseline synthesis verification on specific test target
    res = dev.autonomous_feature_synthesis("Phase 5 baseline integration check", test_target="tests/test_dj_frequency.py")
    assert res["success"] is True
    assert res["author"] == "Architect_Prime"
    assert res["test_results"]["passed"] > 0


def test_daily_briefing_engine_dataview(temp_vault):
    # Create mock agent memories
    agent_mem = Path(temp_vault.vault_root) / "Agents" / "Sentinel_Alpha" / "memories"
    agent_mem.mkdir(parents=True, exist_ok=True)
    (agent_mem / "mem_01.md").write_text("Sample memory content", encoding="utf-8")

    briefing_engine = DailyBriefingEngine(vault_manager=temp_vault)
    res = briefing_engine.generate_daily_briefing(world_day="2026-09-12")

    assert res["success"] is True
    assert res["date"] == "2026-09-12"

    briefing_file = Path(temp_vault.vault_root) / "World" / "daily_briefings.md"
    assert briefing_file.exists()
    content = briefing_file.read_text(encoding="utf-8")
    assert "type: daily-briefing" in content
    assert "[[Sentinel_Alpha]]" in content
    assert "dataview/active" in content

def test_telegram_bot_bridge_phase5_commands(temp_vault):
    dj = DJFrequencyNode()
    bridge = TelegramBotBridge(
        admin_id="123456789",
        vault_manager=temp_vault,
        dj_frequency=dj
    )

    # 1. Frequency shift command
    res_freq = bridge.handle_command("/freq 528", user_id="123456789")
    assert res_freq["success"] is True
    assert "528 Hz" in res_freq["reply"]
    assert dj.get_active_telemetry()["active_frequency_hz"] == 528

    # 2. Bounties check command
    res_bounties = bridge.handle_command("/bounties", user_id="123456789")
    assert res_bounties["success"] is True
    assert "bounties" in res_bounties["reply"].lower()
