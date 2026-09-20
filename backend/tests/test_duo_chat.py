"""
Unit Tests for Orion Prime & Nova Dual-Executive Engine and C2 Router.
"""

import sys
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.vault_manager import VaultManager
from app.services.executive_duo import ExecutiveDuo
from app.routers.c2_executive import router as c2_router


@pytest.fixture
def duo_instance(tmp_path):
    vault = VaultManager(vault_path=tmp_path / "vault")
    return ExecutiveDuo(vault_manager=vault)


@pytest.mark.asyncio
async def test_executive_duo_directive_processing(duo_instance):
    directive = "Scrape competitor wholesale portal, verify MAP violations, and patch security boundary."
    res = await duo_instance.process_directive(directive, operator="Boss")

    assert "orion_response" in res
    assert "nova_response" in res
    assert "tasks" in res
    assert len(res["tasks"]) >= 2

    # Check Orion's tone
    orion_text = res["orion_response"]
    assert "Orion Prime" in orion_text
    assert ("Boss" in orion_text or "pera nei" in orion_text or "plan" in orion_text)

    # Check Nova's tone
    nova_text = res["nova_response"]
    assert "Nova" in nova_text
    assert ("UwU" in nova_text or "✨" in nova_text or "truthful" in nova_text)

    # Check Obsidian vault sync
    note_path = Path(res["obsidian_vault_note"])
    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")
    assert "operator_directive" in content
    assert "importance: 10" in content


def test_c2_executive_router_endpoints(tmp_path):
    import app.routers.c2_executive as c2_mod
    isolated_vault = VaultManager(vault_path=tmp_path / "vault")
    c2_mod._executive_duo = ExecutiveDuo(vault_manager=isolated_vault)

    app = FastAPI()
    app.include_router(c2_router)
    client = TestClient(app)

    # 1. Test duo chat
    chat_resp = client.post("/api/v1/c2/duo-chat", json={"prompt": "Deploy perimeter defense gatekeeper"})
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert "orion_response" in chat_data
    assert "nova_response" in chat_data

    # 2. Test get tasks
    tasks_resp = client.get("/api/v1/c2/tasks")
    assert tasks_resp.status_code == 200
    tasks_data = tasks_resp.json()
    assert "in_progress" in tasks_data
    assert "needs_approval" in tasks_data
    assert "completed" in tasks_data

    # 3. Test groups
    groups_resp = client.get("/api/v1/c2/groups")
    assert groups_resp.status_code == 200
    assert len(groups_resp.json()["groups"]) >= 3

    # 4. Test group chat post and get
    post_resp = client.post("/api/v1/c2/group-chat", json={
        "group_id": "marketing_squad",
        "sender": "Growth_Bot",
        "text": "Outreach campaign dispatched 100 emails."
    })
    assert post_resp.status_code == 200

    get_resp = client.get("/api/v1/c2/group-chat?group_id=marketing_squad")
    assert get_resp.status_code == 200
    msgs = get_resp.json()["messages"]
    assert len(msgs) >= 1
    assert msgs[-1]["sender"] == "Growth_Bot"
