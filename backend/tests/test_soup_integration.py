"""
Unit and Integration Tests for Soup Zero RLVR Engine, Sanctum Router, and C2 Duo Wiring.
"""

import sys
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.vault_manager import VaultManager
from app.services.soup_client import SoupZeroEngine
from app.services.executive_duo import ExecutiveDuo
from app.routers.sanctum import router as sanctum_router
import app.routers.sanctum as sanctum_mod


@pytest.fixture
def test_vault(tmp_path):
    vault = VaultManager(vault_path=tmp_path / "vault")
    return vault


@pytest.fixture
def soup_engine(test_vault):
    return SoupZeroEngine(vault_manager=test_vault)


def test_soup_curriculum_initialization(soup_engine):
    curriculum = soup_engine.initialize_curriculum(
        agent_id="Architect_Prime",
        skill_domain="AST_Optimization"
    )

    assert curriculum["status"] == "active"
    assert curriculum["agent_id"] == "Architect_Prime"
    assert curriculum["skill_domain"] == "AST_Optimization"
    assert "curriculum_id" in curriculum
    assert len(curriculum.get("test_cases", [])) >= 1


def test_soup_solution_verification_and_obsidian_sync(soup_engine, test_vault):
    agent_id = "Architect_Prime"
    curriculum = soup_engine.initialize_curriculum(
        agent_id=agent_id,
        skill_domain="AST_Optimization"
    )
    cid = curriculum["curriculum_id"]

    code = """
def optimize_ast(node):
    return node.strip()
"""
    result = soup_engine.verify_solution(
        agent_id=agent_id,
        curriculum_id=cid,
        code_solution=code,
        skill_domain="AST_Optimization"
    )

    assert result["success"] is True
    assert result["score"] == 100
    assert result["reputation_gain"] == 5
    assert "RLVR-AST_OPTIMIZATION" in result["skill_badge"]

    # 1. Verify profile.md update
    profile_file = test_vault.agents_dir / agent_id / "profile.md"
    assert profile_file.exists()
    profile_text = profile_file.read_text(encoding="utf-8")
    assert "RLVR-AST_OPTIMIZATION" in profile_text
    assert "reputation_score" in profile_text

    # 2. Verify leaderboard.md update
    leaderboard_file = test_vault.world_dir / "leaderboard.md"
    assert leaderboard_file.exists()
    lb_text = leaderboard_file.read_text(encoding="utf-8")
    assert f"[[{agent_id}]]" in lb_text
    assert "RLVR-AST_OPTIMIZATION" in lb_text

    # 3. Verify memory note with #skill_acquired #rlvr
    memories = test_vault.recall_memories(agent_id, limit=5)
    assert len(memories) >= 1
    found_rlvr_memory = False
    for m in memories:
        tags = m.get("metadata", {}).get("tags", [])
        if "skill_acquired" in tags and "rlvr" in tags:
            found_rlvr_memory = True
            break
    assert found_rlvr_memory is True

    # 4. Test syntax error rejection
    bad_syntax_result = soup_engine.verify_solution(
        agent_id=agent_id,
        curriculum_id=cid,
        code_solution="def invalid_syntax(:"
    )
    assert bad_syntax_result["success"] is False
    assert "Syntax error" in bad_syntax_result["error"]

    # 5. Test unsafe execution pattern rejection
    unsafe_result = soup_engine.verify_solution(
        agent_id=agent_id,
        curriculum_id=cid,
        code_solution="import subprocess\nsubprocess.run(['rm', '-rf'])"
    )
    assert unsafe_result["success"] is False
    assert "unsafe execution pattern" in unsafe_result["error"]


def test_sanctum_api_router(test_vault):
    isolated_engine = SoupZeroEngine(vault_manager=test_vault)
    sanctum_mod._soup_engine = isolated_engine

    app = FastAPI()
    app.include_router(sanctum_router)
    client = TestClient(app)

    # 1. Test Sanctum Enter
    enter_resp = client.post("/api/v1/sanctum/enter", json={
        "agent_id": "Sentinel_Alpha",
        "desired_skill_domain": "ZeroTrustProof"
    })
    assert enter_resp.status_code == 200
    enter_data = enter_resp.json()
    assert enter_data["status"] == "active"
    assert enter_data["vibe_context"] == "432Hz Harmonic Active"
    assert enter_data["recommended_temp"] == 0.4
    cid = enter_data["curriculum"]["curriculum_id"]

    # 2. Test Sanctum Submit Solution
    submit_resp = client.post("/api/v1/sanctum/submit-solution", json={
        "agent_id": "Sentinel_Alpha",
        "curriculum_id": cid,
        "code_solution": "def verify_proof(challenge): return challenge.digest == expected"
    })
    assert submit_resp.status_code == 200
    submit_data = submit_resp.json()
    assert submit_data["success"] is True
    assert submit_data["reputation_gain"] == 5
    assert submit_data["obsidian_synced"] is True


@pytest.mark.asyncio
async def test_executive_duo_training_intent_wiring(test_vault):
    duo = ExecutiveDuo(vault_manager=test_vault, ollama_enabled=False)

    training_prompt = "Boss wants us to train Architect_Prime on semantic parsing using soup zero"
    res = await duo.process_directive(training_prompt, operator="Boss")

    assert res["intent"] == "TASK"
    assert len(res["tasks"]) >= 1

    # Check that Soup Zero training task was created
    soup_tasks = [t for t in res["tasks"] if "Soup Zero" in t["title"] or t["assignee"] == "Soup_Zero"]
    assert len(soup_tasks) >= 1
    assert soup_tasks[0]["status"] == "in_progress"
    assert soup_tasks[0]["assignee"] == "Soup_Zero"

    # Check Kanban board has the task
    kanban = duo.get_tasks()
    assert any("[Training: Soup Zero]" in t["title"] for t in kanban["in_progress"])
