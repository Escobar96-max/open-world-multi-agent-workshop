"""
Unit and Integration Tests for Laila (Chief Growth & Market Intelligence Operative).
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
from app.routers.spatial_router import spatial_engine
from app.routers.c2_executive import router as c2_router, NotificationConnectionManager


@pytest.fixture
def app_and_duo(tmp_path):
    vault = VaultManager(vault_path=tmp_path / "vault")
    duo = ExecutiveDuo(vault_manager=vault)
    notifier = NotificationConnectionManager()
    duo.set_notifier(notifier)

    test_app = FastAPI()
    test_app.include_router(c2_router)

    import app.routers.c2_executive as c2_module
    old_duo = c2_module._executive_duo
    old_notifier = c2_module.notifier

    c2_module._executive_duo = duo
    c2_module.notifier = notifier

    yield test_app, duo, notifier

    c2_module._executive_duo = old_duo
    c2_module.notifier = old_notifier


def test_laila_vault_profile_exists():
    vault_profile = BACKEND_DIR.parent / "vault" / "Agents" / "Laila" / "profile.md"
    assert vault_profile.exists()
    content = vault_profile.read_text(encoding="utf-8")
    assert "Laila" in content
    assert "Chief Growth & Market Intelligence Operative" in content
    assert "marketing_squad" in content


def test_laila_spatial_engine_presence():
    assert "Laila" in spatial_engine.agents
    laila = spatial_engine.agents["Laila"]
    assert "Laila" in laila.name
    assert "Growth" in laila.role
    assert laila.x == 28.0
    assert laila.y == 68.0


def test_laila_intent_decomposition(app_and_duo):
    _, duo, _ = app_and_duo
    tasks = duo.decompose_intent("Laila, draft a commercial proposal and analyze competitor pricing for new partners")
    assert len(tasks) >= 1
    laila_tasks = [t for t in tasks if t.assignee == "Laila"]
    assert len(laila_tasks) >= 1
    assert "Market Intelligence" in laila_tasks[0].title or "proposal" in laila_tasks[0].description


@pytest.mark.asyncio
async def test_laila_drain_and_proposal_generation(app_and_duo):
    test_app, duo, notifier = app_and_duo
    client = TestClient(test_app)

    task = TaskCard(
        title="Synthesize Enterprise Partnership Proposal",
        description="Draft partner outreach copy and check MAP violations",
        assignee="Laila",
        status="in_progress",
        priority=9
    )
    duo.tasks.insert(0, task)

    with client.websocket_connect("/api/v1/c2/ws/notifications") as websocket:
        init_data = websocket.receive_json()
        assert init_data["type"] == "connection_established"

        # Drain cycle
        drained = await duo.drain_tasks_step()
        assert drained >= 1
        assert task.status == "completed"
        assert "Market intelligence synthesized" in task.output_summary

        # Check proposal file was written
        proposal_file = duo.vault.vault_path / "World" / "proposals.md"
        assert proposal_file.exists()
        p_content = proposal_file.read_text(encoding="utf-8")
        assert "Laila" in p_content
        assert "Synthesize Enterprise Partnership Proposal" in p_content

        # Check real-time websocket broadcast
        ws_msg = websocket.receive_json()
        assert ws_msg["type"] == "task_completed"
        assert ws_msg["assignee"] == "Laila"
        assert "Orion Prime" in ws_msg["orion_response"]
        assert "Nova" in ws_msg["nova_response"]


def test_marketing_squad_groups_api(app_and_duo):
    test_app, _, _ = app_and_duo
    client = TestClient(test_app)
    res = client.get("/api/v1/c2/groups")
    assert res.status_code == 200
    groups = res.json().get("groups", [])
    mkt = next((g for g in groups if g["id"] == "marketing_squad"), None)
    assert mkt is not None
    assert "Laila" in mkt["lead"]


@pytest.mark.asyncio
async def test_laila_meta_status_update_directive(app_and_duo):
    test_app, duo, _ = app_and_duo
    duo.ollama_enabled = False

    res = await duo.process_directive("check lailas update", operator="Boss")
    assert res["intent"] == "META_QUERY"
    assert res["tasks"] == []

    # Orion acknowledges Laila & The Market Observatory
    assert "Laila" in res["orion_response"]
    assert "The Market Observatory" in res["orion_response"] or "Marketing Squad" in res["orion_response"]

    # Nova provides structured telemetry on Laila
    assert "Laila" in res["nova_response"]
    assert "[28.0, 68.0]" in res["nova_response"]
    assert "UwU" in res["nova_response"]


def test_marketing_squad_direct_chatter_and_laila_reply(app_and_duo):
    test_app, duo, _ = app_and_duo
    client = TestClient(test_app)

    # 1. Verify initial seeded greeting from Laila is present
    get_res = client.get("/api/v1/c2/group-chat?group_id=marketing_squad")
    assert get_res.status_code == 200
    initial_msgs = get_res.json()["messages"]
    assert len(initial_msgs) >= 1
    assert "Laila" in initial_msgs[0]["sender"]

    # 2. Operator asks Laila for status in Marketing Squad channel
    post_res = client.post("/api/v1/c2/group-chat", json={
        "group_id": "marketing_squad",
        "sender": "Operator",
        "text": "Laila, what is the latest status on partner MAP compliance?"
    })
    assert post_res.status_code == 200
    data = post_res.json()
    assert data["success"] is True
    assert data["reply_entry"] is not None
    assert "Laila" in data["reply_entry"]["sender"]
    assert "Station [28.0, 68.0]" in data["reply_entry"]["text"] or "active" in data["reply_entry"]["text"].lower()

    # 3. Operator gives actionable proposal directive
    initial_task_count = len(duo.tasks)
    prop_res = client.post("/api/v1/c2/group-chat", json={
        "group_id": "marketing_squad",
        "sender": "Operator",
        "text": "Laila: draft proposal for new distributor partnership"
    })
    assert prop_res.status_code == 200
    assert prop_res.json()["task_created"] is True
    assert len(duo.tasks) == initial_task_count + 1
    new_task = duo.tasks[0]
    assert new_task.assignee == "Laila"
    assert "Growth Outreach" in new_task.title

