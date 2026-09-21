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
from app.services.executive_duo import ExecutiveDuo, classify_intent
from app.routers.c2_executive import router as c2_router


@pytest.fixture
def duo_instance(tmp_path):
    vault = VaultManager(vault_path=tmp_path / "vault")
    return ExecutiveDuo(vault_manager=vault)


def test_classify_intent_logic():
    # Conversational / Greetings / Banter
    assert classify_intent("kemon acho?") == "CONVERSATION"
    assert classify_intent("ki khobor") == "CONVERSATION"
    assert classify_intent("ki obostha Boss?") == "CONVERSATION"
    assert classify_intent("valovasi") == "CONVERSATION"
    assert classify_intent("valobashi Orion & Nova") == "CONVERSATION"
    assert classify_intent("hello, how are you?") == "CONVERSATION"
    assert classify_intent("thanks a lot!") == "CONVERSATION"
    assert classify_intent("just checking in") == "CONVERSATION"

    # Actionable tasks
    assert classify_intent("Scrape competitor wholesale portal") == "TASK"
    assert classify_intent("run perimeter security check") == "TASK"
    assert classify_intent("send outreach emails to leads") == "TASK"
    assert classify_intent("sort downloaded files") == "TASK"
    assert classify_intent("play 432hz harmonic gaan") == "TASK"
    assert classify_intent("audit recent transactions") == "TASK"

    # Meta Status / Progress / Time Queries
    assert classify_intent("task gulo complete hote kotokhon lagbe?") == "META_QUERY"
    assert classify_intent("task status ki?") == "META_QUERY"
    assert classify_intent("koto time lagbe?") == "META_QUERY"
    assert classify_intent("koto shomoy lagbe?") == "META_QUERY"
    assert classify_intent("task gulo check koro to ki obostha") == "META_QUERY"
    assert classify_intent("baki task gulo koto dur holo?") == "META_QUERY"
    assert classify_intent("sobai ki kaj korche check koro") == "META_QUERY"


@pytest.mark.asyncio
async def test_executive_duo_conversational_chitchat(duo_instance):
    initial_task_count = len(duo_instance.tasks)

    # 1. Test casual greeting
    res = await duo_instance.process_directive("kemon acho?", operator="Boss")

    assert res["intent"] == "CONVERSATION"
    assert res["tasks"] == []
    # Kanban tasks count must remain completely untouched!
    assert len(duo_instance.tasks) == initial_task_count

    # Check Orion's partner tone (warm Banglish, no task boilerplate)
    orion_text = res["orion_response"]
    assert "Orion Prime" in orion_text
    assert "@Architect_Prime" not in orion_text
    assert any(w in orion_text.lower() for w in ["boss", "achi", "ache", "khobor", "obostha", "chill", "bindas", "bhalo", "kemon"])

    # Check Nova's sweet companion tone
    nova_text = res["nova_response"]
    assert "Nova" in nova_text
    assert "UwU" in nova_text or "✨" in nova_text or "🌸" in nova_text
    assert "execution guard" not in nova_text

    # Check Obsidian vault sync
    note_path = Path(res["obsidian_vault_note"])
    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")
    assert "operator_chat" in content
    assert "type: conversation" in content

    # 2. Test affection message
    res2 = await duo_instance.process_directive("valovasi", operator="Boss")
    assert res2["intent"] == "CONVERSATION"
    assert res2["tasks"] == []
    assert len(duo_instance.tasks) == initial_task_count


@pytest.mark.asyncio
async def test_executive_duo_agent_interaction_query_and_history(duo_instance):
    # Verify world context reads active agents
    world_ctx = duo_instance.get_world_context()
    assert "Architect_Prime" in world_ctx or "Agents active" in world_ctx

    # User asks specific question about other agents
    prompt = "tomader ke sathe niye amaro valo lagche , tomra baki agents der sathe interact korecho?"
    res = await duo_instance.process_directive(prompt, operator="Boss")

    assert res["intent"] == "CONVERSATION"
    orion_text = res["orion_response"]
    # Must specifically reference agents / activity, NOT a canned coffee phrase
    assert any(a in orion_text for a in ["Architect", "DJ", "Sentinel", "agent", "squad", "Lounge", "Plaza", "active"])
    assert "Ek cup coffee niye ektu adda" not in orion_text

    # Multi-turn history must have recorded the exchange
    assert len(duo_instance.history) >= 2
    assert duo_instance.history[-2]["role"] == "user"
    assert duo_instance.history[-2]["content"] == prompt
    assert duo_instance.history[-1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_executive_duo_directive_processing(duo_instance):
    initial_task_count = len(duo_instance.tasks)
    directive = "Scrape competitor wholesale portal, verify MAP violations, and patch security boundary."
    res = await duo_instance.process_directive(directive, operator="Boss")

    assert res["intent"] == "TASK"
    assert "orion_response" in res
    assert "nova_response" in res
    assert "tasks" in res
    assert len(res["tasks"]) >= 2
    # Tasks added to Kanban board
    assert len(duo_instance.tasks) > initial_task_count

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

    # 5. Test manual drain cycle endpoint
    drain_resp = client.post("/api/v1/c2/tasks/drain")
    assert drain_resp.status_code == 200
    assert drain_resp.json()["success"] is True


@pytest.mark.asyncio
async def test_executive_duo_meta_query_and_task_grounding(duo_instance):
    """
    Validates that meta-queries about ongoing tasks or time estimates:
    1. Do NOT create new TaskCards on the Kanban board.
    2. Ground Orion's response in the current active task board summary.
    3. Return realistic status / time estimations.
    """
    summary = duo_instance.get_task_board_summary()
    assert "Active Kanban State:" in summary
    assert "in-progress" in summary

    initial_task_count = len(duo_instance.tasks)
    meta_prompt = "task gulo complete hote kotokhon lagbe?"
    res = await duo_instance.process_directive(meta_prompt, operator="Boss")

    assert res["intent"] in ["META_QUERY", "CONVERSATION"]
    # Kanban tasks count must remain completely untouched!
    assert len(res["tasks"]) == 0
    assert len(duo_instance.tasks) == initial_task_count

    orion_text = res["orion_response"]
    assert "Orion Prime" in orion_text
    # Should include time estimation / status reassurance, NOT a task delegation DAG
    assert any(w in orion_text.lower() for w in ["minute", "lagbe", "task", "control", "chill", "completed", "squad"])
    assert "Tasks divide" not in orion_text


@pytest.mark.asyncio
async def test_executive_duo_autonomous_worker_drain(duo_instance):
    """
    Validates that the autonomous task worker successfully executes and drains
    in-progress tasks to completed with domain output summaries.
    """
    # Seed an in-progress task for Vlone_Browser
    from app.services.executive_duo import TaskCard
    test_task = TaskCard(
        title="Test Vlone Surveillance Run",
        description="Headless inspection test",
        assignee="Vlone_Browser",
        status="in_progress"
    )
    duo_instance.tasks.insert(0, test_task)

    # Initial state check
    in_prog_before = [t for t in duo_instance.tasks if t.status == "in_progress"]
    assert len(in_prog_before) >= 1

    # Execute one autonomous drain step
    drained_count = await duo_instance.drain_tasks_step()
    assert drained_count >= 1

    # Verify task is now completed with output summary
    completed_task = next(t for t in duo_instance.tasks if t.id == test_task.id)
    assert completed_task.status == "completed"
    assert completed_task.output_summary is not None
    assert "Vlone" in completed_task.output_summary or "DOM" in completed_task.output_summary


def test_resolve_responder_logic():
    from app.services.executive_duo import resolve_responder
    assert resolve_responder("full agent world er update ki Nova?") == "NOVA_ONLY"
    assert resolve_responder("Nova, kemon acho?") == "NOVA_ONLY"
    assert resolve_responder("Orion, status bolo") == "ORION_ONLY"
    assert resolve_responder("Orion Prime ki obostha?") == "ORION_ONLY"
    assert resolve_responder("Orion and Nova, shob thik ache to?") == "DUO"
    assert resolve_responder("kemon acho?") == "DUO"
    assert resolve_responder("all other agents der ki obostha ! last few days er tader kajer upodate ki?") == "DUO"


@pytest.mark.asyncio
async def test_executive_duo_targeted_single_agent_routing(duo_instance):
    # 1. Targeted Nova Query
    res_nova = await duo_instance.process_directive("full agent world er update ki Nova?", operator="Boss")
    assert res_nova["responder"] == "NOVA_ONLY"
    assert res_nova["orion_response"] is None
    assert res_nova["nova_response"] is not None
    assert "Nova" in res_nova["nova_response"]

    # 2. Targeted Orion Query
    res_orion = await duo_instance.process_directive("Orion, status bolo", operator="Boss")
    assert res_orion["responder"] == "ORION_ONLY"
    assert res_orion["nova_response"] is None
    assert res_orion["orion_response"] is not None
    assert "Orion Prime" in res_orion["orion_response"]


@pytest.mark.asyncio
async def test_executive_duo_multi_day_vault_memory_recall(duo_instance):
    from app.services.executive_duo import is_multi_day_query
    prompt = "all other agents der ki obostha ! last few days er tader kajer upodate ki?"
    assert is_multi_day_query(prompt) is True

    res = await duo_instance.process_directive(prompt, operator="Boss")
    assert res["responder"] == "DUO"
    assert res["intent"] == "META_QUERY"
    assert res["tasks"] == []

    # Verify that multi-day summary or agent status is reflected in either Orion or Nova's response
    combined_response = (res["orion_response"] or "") + " " + (res["nova_response"] or "")
    assert any(w in combined_response for w in ["Architect", "DJ", "Sentinel", "Vlone", "vault", "task", "online", "active"])


