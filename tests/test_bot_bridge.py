import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from services.bot_bridge import TelegramBotBridge
from services.telegram_notifier import TelegramNotifier
from services.spatial_engine import SpatialEngine
from services.dj_frequency import DJFrequencyNode
from services.ledger_service import LedgerService
from services.vault_manager import VaultManager
from api.telegram_router import router as telegram_router

app = FastAPI()
app.include_router(telegram_router)
client = TestClient(app)

@pytest.fixture
def test_bridge(tmp_path):
    vm = VaultManager(vault_root=str(tmp_path))
    vm.ensure_vault_hierarchy()
    se = SpatialEngine(vault_manager=vm)
    dj = DJFrequencyNode()
    ledger = LedgerService()
    bridge = TelegramBotBridge(
        bot_token="test_bot_token",
        admin_id="999888777",
        spatial_engine=se,
        dj_frequency=dj,
        ledger_service=ledger,
        vault_manager=vm
    )
    return bridge

def test_public_help_command(test_bridge):
    # Any user can invoke /help or /start
    res = test_bridge.handle_command("/help", user_id="random_stranger")
    assert res["success"] is True
    assert "Autonomous AI Open-World Telegram C2 Bridge" in res["reply"]

def test_authorization_rejection(test_bridge):
    # Non-admin user attempts privileged /status
    res = test_bridge.handle_command("/status", user_id="unauthorized_intruder")
    assert res["success"] is False
    assert res.get("error") == "UNAUTHORIZED"
    assert "Access Denied" in res["reply"]

def test_privileged_commands_execution(test_bridge):
    admin = "999888777"

    # 1. /status
    res_status = test_bridge.handle_command("/status", user_id=admin)
    assert res_status["success"] is True
    assert "Ecosystem Status Report" in res_status["reply"]

    # 2. /frequency
    res_freq = test_bridge.handle_command("/frequency", user_id=admin)
    assert res_freq["success"] is True
    assert "DJ Frequency Node" in res_freq["reply"]

    # 3. /balance
    res_bal = test_bridge.handle_command("/balance Sentinel_Alpha", user_id=admin)
    assert res_bal["success"] is True
    assert res_bal["balance"] == 500.0

    # 4. /teleport
    res_tp = test_bridge.handle_command("/teleport Sentinel_Alpha 65.0 70.0", user_id=admin)
    assert res_tp["success"] is True
    assert "Frequency Lounge" in res_tp["result"]["zone"]
    # Verify spatial position
    pos = test_bridge.spatial_engine.get_agent_position("Sentinel_Alpha")
    assert pos["x"] == 65.0
    assert pos["y"] == 70.0

    # 5. /broadcast
    res_bc = test_bridge.handle_command("/broadcast Nightly convergence initiated", user_id=admin)
    assert res_bc["success"] is True
    assert "Ambient Broadcast Transmitted" in res_bc["reply"]

import asyncio

def test_telegram_update_webhook_processing(test_bridge):
    async def _run():
        update_payload = {
            "update_id": 10001,
            "message": {
                "message_id": 42,
                "from": {"id": 999888777, "first_name": "AdminOperator"},
                "chat": {"id": 999888777, "type": "private"},
                "text": "/status"
            }
        }
        result = await test_bridge.process_telegram_update(update_payload)
        assert result["status"] == "PROCESSED"
        assert result["user_id"] == 999888777
        assert result["response"]["success"] is True
    asyncio.run(_run())

def test_telegram_notifier_events():
    async def _run():
        notifier = TelegramNotifier(bot_token="mock_token", channel_id="test_channel")

        # 1. Gatekeeper clearance alert
        a1 = await notifier.notify_gatekeeper_clearance("Sentinel_Alpha", challenge_difficulty=4)
        assert a1["delivered"] is True
        assert a1["type"] == "GATEKEEPER_CLEARANCE"

        # 2. Sanctum graduation alert
        a2 = await notifier.notify_sanctum_graduation("Sentinel_Alpha", "Recursive Fibonacci", level=2, xp_awarded=50)
        assert a2["delivered"] is True
        assert a2["type"] == "SANCTUM_GRADUATION"

        # 3. Bounty claim alert
        a3 = await notifier.notify_bounty_event("CLAIMED", "bounty_123", "Inspect Perimeter", 120.0, "Curator_Node")
        assert a3["delivered"] is True
        assert a3["type"] == "BOUNTY_CLAIMED"

        # 4. Security alert
        a4 = await notifier.notify_security_alert("REPLAY_ATTACK", "Nonce reused by unknown agent")
        assert a4["delivered"] is True
        assert a4["type"] == "SECURITY_ALERT"

        assert len(notifier.sent_alerts) == 4
    asyncio.run(_run())

def test_telegram_api_router_endpoints(monkeypatch):
    from api import telegram_router as tr
    test_bridge_instance = TelegramBotBridge(admin_id="999888777")
    monkeypatch.setattr(tr, "bot_bridge", test_bridge_instance)

    # 1. GET /api/v1/telegram/status
    resp = client.get("/api/v1/telegram/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ONLINE"

    # 2. POST /api/v1/telegram/webhook
    resp = client.post(
        "/api/v1/telegram/webhook",
        json={
            "update_id": 10002,
            "message": {
                "message_id": 43,
                "from": {"id": 999888777},
                "chat": {"id": 999888777},
                "text": "/help"
            }
        }
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PROCESSED"
