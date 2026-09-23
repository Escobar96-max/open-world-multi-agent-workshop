"""
Tests for Proactive Real-Time Notifications, WebSocket Bus, and Agent Questions.
"""

import sys
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.vault_manager import VaultManager
from app.services.executive_duo import ExecutiveDuo, TaskCard
from app.routers.c2_executive import router as c2_router, NotificationConnectionManager


@pytest.fixture
def app_and_duo(tmp_path):
    vault = VaultManager(vault_path=tmp_path / "vault")
    duo = ExecutiveDuo(vault_manager=vault)
    notifier = NotificationConnectionManager()
    duo.set_notifier(notifier)

    test_app = FastAPI()
    test_app.include_router(c2_router)

    # Patch router's singleton for testing
    import app.routers.c2_executive as c2_module
    old_duo = c2_module._executive_duo
    old_notifier = c2_module.notifier

    c2_module._executive_duo = duo
    c2_module.notifier = notifier

    yield test_app, duo, notifier

    c2_module._executive_duo = old_duo
    c2_module.notifier = old_notifier


def test_notification_connection_manager_lifecycle():
    mgr = NotificationConnectionManager()
    assert len(mgr.active_connections) == 0


def test_websocket_connection_and_proactive_notify(app_and_duo):
    test_app, duo, notifier = app_and_duo
    client = TestClient(test_app)

    with client.websocket_connect("/api/v1/c2/ws/notifications") as websocket:
        init_data = websocket.receive_json()
        assert init_data["type"] == "connection_established"
        assert "Connected" in init_data["message"]

        # Post a proactive question via REST /notify
        notify_res = client.post("/api/v1/c2/notify", json={
            "sender": "Nova",
            "message": "Boss, should I initiate deep semantic crawling?",
            "category": "question",
            "options": ["Yes, start crawling", "Hold for now"]
        })
        assert notify_res.status_code == 200
        assert notify_res.json()["success"] is True

        # Verify that WebSocket client immediately received the proactive question!
        ws_msg = websocket.receive_json()
        assert ws_msg["type"] == "agent_question"
        assert ws_msg["sender"] == "Nova"
        assert "should I initiate deep semantic crawling?" in ws_msg["nova_response"]
        assert ws_msg["options"] == ["Yes, start crawling", "Hold for now"]


@pytest.mark.asyncio
async def test_drain_tasks_step_proactive_broadcast(app_and_duo):
    test_app, duo, notifier = app_and_duo
    client = TestClient(test_app)

    # Create a task in progress
    test_task = TaskCard(
        title="Check MAP Violations",
        description="Run Vlone semantic check",
        assignee="Vlone_Browser",
        status="in_progress",
        priority=8
    )
    duo.tasks.insert(0, test_task)

    with client.websocket_connect("/api/v1/c2/ws/notifications") as websocket:
        init_data = websocket.receive_json()
        assert init_data["type"] == "connection_established"

        # Drain the task
        drained = await duo.drain_tasks_step()
        assert drained >= 1

        # The WebSocket client must proactively receive the task_completed notification!
        ws_msg = websocket.receive_json()
        assert ws_msg["type"] == "task_completed"
        assert ws_msg["task_id"] == test_task.id
        assert ws_msg["assignee"] == "Vlone_Browser"
        assert "Orion Prime" in ws_msg["orion_response"]
        assert "Nova" in ws_msg["nova_response"]
        assert "Check MAP Violations" in ws_msg["orion_response"]


def test_approve_task_proactive_broadcast(app_and_duo):
    test_app, duo, notifier = app_and_duo
    client = TestClient(test_app)

    # Create a task needing approval
    test_task = TaskCard(
        title="Deploy Perimeter Firewall",
        description="Gatekeeper zero-trust lock",
        assignee="Sentinel_Alpha",
        status="needs_approval",
        priority=10
    )
    duo.tasks.insert(0, test_task)

    with client.websocket_connect("/api/v1/c2/ws/notifications") as websocket:
        init_data = websocket.receive_json()
        assert init_data["type"] == "connection_established"

        # Approve the task via REST
        res = client.post("/api/v1/c2/tasks/approve", json={"task_id": test_task.id})
        assert res.status_code == 200
        assert res.json()["success"] is True

        # Check notification was broadcast
        ws_msg = websocket.receive_json()
        assert ws_msg["type"] == "task_approved"
        assert ws_msg["task_id"] == test_task.id
        assert "Boss approved" in ws_msg["nova_response"]
