"""
Integration and Unit Tests for:
Agent Profiles & Multi-Source Training Ground Panel
- AgentTrainingGround (Web Sweep + YouTube Digest + Soup Zero RLVR + Obsidian Vault Sync)
- REST API Endpoints (/api/v1/training/agents, /agent/{id}, /assign, /status/{id})
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from app.services.training_ground import AgentTrainingGround, training_ground


@pytest.fixture
def custom_training_ground(tmp_path):
    vault_agents = tmp_path / "vault" / "Agents"
    vault_agents.mkdir(parents=True, exist_ok=True)
    return AgentTrainingGround(vault_base=vault_agents)


def test_agent_profiles_reading_and_defaults(custom_training_ground):
    profile = custom_training_ground.get_agent_profile("Bob")
    assert profile["agent_id"] == "Bob"
    assert profile["name"] == "Bob"
    assert "Spatial Math" in profile["role"]
    assert "Euclidean" in profile["specialized_in"]
    assert profile["progress_pct"] == 0
    assert profile["current_stage"] == "Idle"

    # Dr. Aris normalization
    profile_aris = custom_training_ground.get_agent_profile("Dr._Aris")
    assert profile_aris["agent_id"] == "Dr_Aris"
    assert "Diagnostic" in profile_aris["role"]


@pytest.mark.asyncio
async def test_multi_source_training_pipeline_execution(custom_training_ground):
    agent_id = "Bob"
    topic = "FastAPI Async WebSockets Optimization"
    task = "Implement low-latency heartbeat broadcast with auto-reconnect"

    # Execute training loop
    await custom_training_ground.launch_agent_training(
        agent_id=agent_id,
        topic=topic,
        specific_task=task
    )

    # Verify final completed state
    profile = custom_training_ground.get_agent_profile(agent_id)
    assert profile["progress_pct"] == 100
    assert profile["current_stage"] == "Training Completed & Skill Logged"
    assert profile["current_topic"] == topic
    assert profile["stages_completed"]["web_docs"] is True
    assert profile["stages_completed"]["youtube_transcript"] is True
    assert profile["stages_completed"]["soup_pytest"] is True
    assert profile["stages_completed"]["vault_persisted"] is True

    # Verify vault persistence
    profile_file = Path(profile["vault_path"])
    assert profile_file.exists()
    content = profile_file.read_text(encoding="utf-8")
    assert topic in content
    assert "#skill_acquired" in content
    assert "Web+YouTube+SoupZero" in content

    # Verify acquired skills list parsed from vault
    assert any(topic in s for s in profile["acquired_skills"])


def test_training_ground_api_endpoints():
    client = TestClient(app)

    # 1. List all agents
    res_list = client.get("/api/v1/training/agents")
    assert res_list.status_code == 200
    agents = res_list.json()
    assert len(agents) >= 6
    agent_ids = [a["agent_id"] for a in agents]
    assert "Bob" in agent_ids
    assert "Moly" in agent_ids
    assert "Laila" in agent_ids
    assert "Architect_Prime" in agent_ids

    # 2. Inspect specific agent profile
    res_single = client.get("/api/v1/training/agent/Moly")
    assert res_single.status_code == 200
    moly_data = res_single.json()
    assert moly_data["name"] == "Moly"
    assert "Lead Intelligence" in moly_data["role"]

    # 3. Assign new training
    res_assign = client.post("/api/v1/training/assign", json={
        "agent_id": "Moly",
        "topic": "Advanced OSINT Thread Traversal",
        "task": "Mine decision maker reaction graphs on LinkedIn threads"
    })
    assert res_assign.status_code == 200
    assign_data = res_assign.json()
    assert assign_data["status"] == "started"
    assert assign_data["agent_id"] == "Moly"
    assert assign_data["topic"] == "Advanced OSINT Thread Traversal"

    # 4. Status endpoint
    res_status = client.get("/api/v1/training/status/Moly")
    assert res_status.status_code == 200
    status_data = res_status.json()
    assert status_data["agent_id"] == "Moly"
    assert "current_stage" in status_data
