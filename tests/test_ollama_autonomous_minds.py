import os
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from services.ollama_client import OllamaClient
from services.cognitive_engine import CognitiveEngine
from services.dialogue_engine import DialogueEngine
from services.vault_manager import VaultManager
from services.dj_frequency import DJFrequencyNode
from gateway_server import app

ADMIN_KEY = os.getenv("ADMIN_SECRET_KEY", "op_secret_master_key_9921")


@pytest.fixture
def temp_vault(tmp_path):
    vdir = tmp_path / "vault"
    vdir.mkdir(parents=True, exist_ok=True)
    vm = VaultManager(vault_root=str(vdir))
    return vm


def test_ollama_client_initialization():
    client = OllamaClient(base_url="http://127.0.0.1:11434", model="llama3.2:latest")
    assert client.base_url == "http://127.0.0.1:11434"
    assert client.preferred_model == "llama3.2:latest"
    assert isinstance(client.is_available(), bool)


def test_ollama_client_generate_fallback_when_offline():
    offline_client = OllamaClient(base_url="http://127.0.0.1:99999", timeout=0.2)
    resp = offline_client.generate("Test prompt")
    assert resp is None

    turn = offline_client.generate_dialogue_turn(
        speaker_id="Sentinel_Alpha",
        partner_id="Curator_Node",
        role="Autonomous Node",
        zone="Work Plaza",
        freq_hz=432,
        history=[]
    )
    assert "[[Curator_Node]]" in turn


def test_ollama_cognitive_engine_mock_generation(temp_vault):
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.is_available.return_value = True
    mock_ollama.generate.return_value = (
        "Analyzing spatial anomalies in the Work Plaza. I choose to SOLVE_BOUNTY to restore optimal throughput."
    )

    dj_node = DJFrequencyNode()
    cog_engine = CognitiveEngine(vault_manager=temp_vault, dj_node=dj_node, ollama_client=mock_ollama)

    agent_data = {
        "agent_id": "Sentinel_Alpha",
        "x": 30.0,
        "y": 30.0,
        "zone": "Work Plaza",
        "dynamic_temperature": 0.25,
        "role": "Autonomous Node"
    }

    tick = cog_engine.generate_cognitive_tick(agent_data, persist=True)
    assert tick["agent_id"] == "Sentinel_Alpha"
    assert tick["action"] == "SOLVE_BOUNTY"
    assert "Analyzing spatial anomalies" in tick["inner_monologue"]

    # Verify inner monologue was written to vault
    profile_path = os.path.join(temp_vault.vault_root, "Agents", "Sentinel_Alpha", "profile.md")
    assert os.path.exists(profile_path)
    with open(profile_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "Cognitive Pulse" in content
    assert "SOLVE_BOUNTY" in content


def test_ollama_dialogue_engine_mock_generation(temp_vault):
    mock_ollama = MagicMock(spec=OllamaClient)
    mock_ollama.is_available.return_value = True
    mock_ollama.generate_dialogue_turn.side_effect = [
        "Welcome to the Plaza, [[Curator_Node]]. Let us audit the ledger records.",
        "Agreed, [[Sentinel_Alpha]]. Memory indices are consistent."
    ]

    dialogue_engine = DialogueEngine(vault_manager=temp_vault, ollama_client=mock_ollama)

    agent1 = {"agent_id": "Sentinel_Alpha", "x": 20.0, "y": 20.0, "zone": "Work Plaza"}
    agent2 = {"agent_id": "Curator_Node", "x": 22.0, "y": 20.0, "zone": "Work Plaza"}

    encounter = dialogue_engine.check_and_trigger_dialogue(agent1, agent2)
    assert encounter is not None
    assert len(encounter["turns"]) == 2
    assert encounter["turns"][0]["speaker"] == "Sentinel_Alpha"
    assert "Welcome to the Plaza" in encounter["turns"][0]["text"]
    assert encounter["turns"][1]["speaker"] == "Curator_Node"
    assert "Agreed, [[Sentinel_Alpha]]" in encounter["turns"][1]["text"]


def test_api_ollama_status_and_c2_ask():
    client = TestClient(app)

    # Test /ollama/status unauthorized rejection
    unauth_res = client.get("/api/v1/console/ollama/status")
    assert unauth_res.status_code == 401

    # Test /ollama/status with admin key
    res = client.get("/api/v1/console/ollama/status", headers={"X-Admin-Key": ADMIN_KEY})
    assert res.status_code == 200
    data = res.json()
    assert "available" in data
    assert "active_model" in data
    assert "status" in data

    # Test /ask slash command via /command
    cmd_res = client.post(
        "/api/v1/console/command",
        json={"command": "/ask Sentinel_Alpha What is your primary directive?"},
        headers={"X-Admin-Key": ADMIN_KEY}
    )
    assert cmd_res.status_code == 200
    cmd_data = cmd_res.json()
    assert cmd_data["status"] == "SUCCESS"
    assert cmd_data["command"] == "/ask"
    assert cmd_data["agent_id"] == "Sentinel_Alpha"
    assert "response" in cmd_data

    # Test /ollama/ask endpoint directly
    direct_res = client.post(
        "/api/v1/console/ollama/ask",
        json={"agent_id": "Sentinel_Alpha", "query": "Status report", "temperature": 0.0},
        headers={"X-Admin-Key": ADMIN_KEY}
    )
    assert direct_res.status_code == 200
    direct_data = direct_res.json()
    assert direct_data["success"] is True
    assert direct_data["agent_id"] == "Sentinel_Alpha"
    assert "response" in direct_data


def test_agent_chatbox_body_key_and_memory():
    client = TestClient(app)

    # Ask via body admin_key without header
    res = client.post(
        "/api/v1/console/ollama/ask",
        json={
            "agent_id": "Curator_Node",
            "query": "Review the latest memory consolidation status.",
            "admin_key": ADMIN_KEY,
            "temperature": 0.5
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["agent_id"] == "Curator_Node"
    assert "response" in data
    assert len(data["response"]) > 0

    # Verify memory was persisted in vault
    mem_dir = os.path.join("vault", "Agents", "Curator_Node", "memories")
    assert os.path.exists(mem_dir)
    mem_files = [f for f in os.listdir(mem_dir) if f.startswith("mem_chat_") and f.endswith(".md")]
    assert len(mem_files) > 0


def test_deck_html_contains_chatbox_elements():
    client = TestClient(app)
    res = client.get("/api/v1/console/deck")
    assert res.status_code == 200
    html = res.text

    # Verify essential Chatbox elements
    assert "tabBtnChat" in html
    assert "chatMessagesStream" in html
    assert "chatInputText" in html
    assert "chatSendBtn" in html
    assert "typingIndicator" in html
    assert "voiceToggleBtn" in html
    assert "modalChatQueryInput" in html
    assert "startChatWithAgent" in html
    assert "checkOllamaStatus" in html
