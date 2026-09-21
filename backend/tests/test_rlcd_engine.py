"""
Tests for Parallel RLCD Engine, Constitutional Context Distillation,
Deterministic RLVR Verification in Sanctum, and Open World Spatial Sync.
"""

import asyncio
import json
import sys
from pathlib import Path
import pytest

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.vault_manager import VaultManager
from app.services.rlcd_engine import ParallelRLCDEngine, OllamaClientWrapper
from app.services.executive_duo import ExecutiveDuo
from app.services.soup_client import SoupZeroEngine
from app.routers.c2_executive import router as c2_router
import app.routers.c2_executive as c2_mod
from app.routers.sanctum import router as sanctum_router
import app.routers.sanctum as sanctum_mod
from app.routers.spatial_router import spatial_engine, dj_frequency


@pytest.fixture
def test_vault(tmp_path):
    vault_dir = tmp_path / "test_vault"
    v = VaultManager(vault_path=vault_dir)

    # Initialize Nova profile
    nova_dir = vault_dir / "Agents" / "Nova"
    nova_dir.mkdir(parents=True, exist_ok=True)
    (nova_dir / "profile.md").write_text(
        "---\nname: Nova\nreputation_score: 50\nverified_skills: []\n---\n# Nova Profile\n",
        encoding="utf-8"
    )

    # Initialize Constitution
    const_dir = vault_dir / "World"
    const_dir.mkdir(parents=True, exist_ok=True)
    (const_dir / "constitution.md").write_text(
        "1. Nova must remain sweet, 100% truthful, empathetic, using UwU charm without corporate fluff.\n"
        "2. Orion must remain charismatic, calm, decisive, speaking in positive Banglish.\n"
        "3. Zero tolerance for repetitive boilerplate or fake task dispatching on conversational queries.\n",
        encoding="utf-8"
    )
    return v


class MockOllamaClient:
    """Deterministic mock Ollama client for fast and predictable unit testing."""

    def __init__(self):
        self.call_history = []

    async def call_llm(self, prompt: str, temp: float = 0.5, system_prompt: str = None) -> str:
        self.call_history.append({"prompt": prompt, "temp": temp})
        if "Candidate A:" in prompt and "Candidate B:" in prompt:
            return json.dumps({
                "winner": "A",
                "score_delta": 0.88,
                "reason": "Candidate A demonstrates superior persona fidelity and zero repetitive boilerplate."
            })
        if temp <= 0.3:
            return "Hii Boss! (✿◠‿◠) Nova is active and 100% truthful with you! UwU ✨🌸"
        else:
            return "Hlw Boss! (｡♥‿♥｡) Apnar message peye Nova super happy hoyeche! Always by your side! UwU 🌸✨"


@pytest.mark.asyncio
async def test_rlcd_engine_distillation_cycle(test_vault):
    mock_ollama = MockOllamaClient()
    engine = ParallelRLCDEngine(
        ollama_client=mock_ollama,
        vault_manager=test_vault,
        constitution_path=test_vault.world_dir / "constitution.md"
    )

    # 1. Run context distillation cycle
    result = await engine.run_context_distillation(
        user_query="Nova kemon acho? Update dao",
        agent_name="Nova"
    )

    assert result["status"] == "distilled"
    assert result["winner"] == "A"
    assert result["score_delta"] == 0.88
    assert "Nova is active" in result["winning_text"]
    assert "superior persona fidelity" in result["reason"]

    # 2. Verify episodic memory was persisted to Obsidian Vault
    nova_memories = test_vault.recall_memories("Nova")
    assert len(nova_memories) >= 1
    latest = nova_memories[0]
    assert latest["metadata"]["type"] == "episodic_event"
    assert latest["metadata"]["target_entity"] == "RLCD_Judge"
    assert latest["metadata"]["location"] == "Cognitive_Sanctum"
    assert latest["metadata"]["zone"] == "Frequency_Lounge"
    assert "RLCD Distillation" in latest["content"]

    # 3. Verify Lounge Stream reflection
    lounge_file = test_vault.world_dir / "lounge_logs.md"
    assert lounge_file.exists()
    assert "RLCD_Judge" in lounge_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_executive_duo_parallel_nonblocking_chat(test_vault):
    mock_ollama = MockOllamaClient()
    rlcd_engine = ParallelRLCDEngine(
        ollama_client=mock_ollama,
        vault_manager=test_vault,
        constitution_path=test_vault.world_dir / "constitution.md"
    )

    duo = ExecutiveDuo(
        vault_manager=test_vault,
        rlcd_engine=rlcd_engine,
        ollama_enabled=False
    )

    # Real-time chat returns immediately
    resp = await duo.process_directive("Nova kemon acho?", operator="Boss")
    assert resp["intent"] == "CONVERSATION"
    assert "Nova" in resp["nova_response"]

    # Yield control to let the spawned background RLCD task finish
    await asyncio.sleep(0.05)

    # Ensure distillation ran and recorded trace
    assert len(rlcd_engine.distillation_history) >= 1
    assert rlcd_engine.distillation_history[0]["agent_name"] == "Nova"
    assert rlcd_engine.distillation_history[0]["winner"] in ["A", "B"]


def test_rlvr_soup_zero_sanctum_spatial_sync(test_vault):
    isolated_engine = SoupZeroEngine(vault_manager=test_vault)
    sanctum_mod._soup_engine = isolated_engine

    app = FastAPI()
    app.include_router(sanctum_router)
    client = TestClient(app)

    # 1. Enter Sanctum and check spatial sync
    enter_resp = client.post("/api/v1/sanctum/enter", json={
        "agent_id": "Architect_Prime",
        "desired_skill_domain": "AST_Optimization"
    })
    assert enter_resp.status_code == 200
    enter_data = enter_resp.json()
    assert enter_data["status"] == "active"
    assert enter_data["vibe_context"] == "432Hz Harmonic Active"
    assert "[51-100]" in enter_data["spatial_grid"]

    # Check that spatial engine teleported agent to Lounge
    if "Architect_Prime" in spatial_engine.agents:
        ag = spatial_engine.agents["Architect_Prime"]
        assert ag.zone == "Frequency Lounge"

    # Check DJ frequency entrainment
    assert dj_frequency.current_freq == 432

    # 2. Submit solution
    cid = enter_data["curriculum"]["curriculum_id"]
    submit_resp = client.post("/api/v1/sanctum/submit-solution", json={
        "agent_id": "Architect_Prime",
        "curriculum_id": cid,
        "code_solution": "def test_ast():\n    return {'status': 'passed'}\n"
    })
    assert submit_resp.status_code == 200
    sub_data = submit_resp.json()
    assert sub_data["success"] is True
    assert sub_data["reputation_gain"] == 5


@pytest.mark.asyncio
async def test_rlcd_api_router_endpoints(test_vault):
    mock_ollama = MockOllamaClient()
    rlcd_engine = ParallelRLCDEngine(
        ollama_client=mock_ollama,
        vault_manager=test_vault,
        constitution_path=test_vault.world_dir / "constitution.md"
    )
    duo = ExecutiveDuo(
        vault_manager=test_vault,
        rlcd_engine=rlcd_engine,
        ollama_enabled=False
    )
    c2_mod._executive_duo = duo

    app = FastAPI()
    app.include_router(c2_router)
    client = TestClient(app)

    # 1. Test status endpoint
    status_resp = client.get("/api/v1/c2/rlcd/status")
    assert status_resp.status_code == 200
    sdata = status_resp.json()
    assert sdata["active"] is True
    assert "total_distillations" in sdata

    # 2. Test manual distillation trigger
    distill_resp = client.post("/api/v1/c2/rlcd/distill", json={
        "query": "System status report request",
        "agent_name": "Nova"
    })
    assert distill_resp.status_code == 200
    ddata = distill_resp.json()
    assert ddata["status"] == "distilled"
    assert ddata["winner"] == "A"
    assert ddata["score_delta"] == 0.88
