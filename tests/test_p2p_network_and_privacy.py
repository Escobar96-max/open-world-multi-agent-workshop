import os
import pytest
from fastapi.testclient import TestClient

from services.agent_identity import AgentIdentityService
from services.p2p_mesh import P2PMeshService
from gateway_server import app

ADMIN_KEY = os.getenv("ADMIN_SECRET_KEY", "op_secret_master_key_9921")


@pytest.fixture
def identity_service(tmp_path):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)
    return AgentIdentityService(vault_root=str(vault_dir))


def test_agent_identity_creation_and_did(identity_service):
    ident = identity_service.get_or_create_identity("Sentinel_Alpha")
    assert ident["agent_id"] == "Sentinel_Alpha"
    assert ident["did"].startswith("did:agent:ed25519:")
    assert len(ident["signing_public_key"]) == 64
    assert len(ident["encryption_public_key"]) == 64
    assert ident["enclave_status"] == "SECURED"

    # Verify idempotency
    ident2 = identity_service.get_or_create_identity("Sentinel_Alpha")
    assert ident2["did"] == ident["did"]
    assert ident2["signing_public_key"] == ident["signing_public_key"]


def test_agent_payload_signing_and_verification(identity_service):
    payload = {"agent_id": "Sentinel_Alpha", "x": 42.0, "y": 88.0, "status": "PATROLLING"}
    sig = identity_service.sign_payload("Sentinel_Alpha", payload)
    assert isinstance(sig, str) and len(sig) > 0

    # Verification success
    assert identity_service.verify_signature("Sentinel_Alpha", payload, sig) is True

    # Verification failure on tampered payload
    tampered_payload = dict(payload)
    tampered_payload["status"] = "BREACHED"
    assert identity_service.verify_signature("Sentinel_Alpha", tampered_payload, sig) is False


def test_e2e_whisper_encryption_and_decryption(identity_service):
    secret_text = "CLASSIFIED_MISSION: Relocate to Frequency Lounge at 0400 for consensus alignment."
    
    # Encrypt transmission from Sentinel_Alpha to Curator_Node
    whisper = identity_service.encrypt_whisper(
        sender_id="Sentinel_Alpha",
        recipient_id="Curator_Node",
        plaintext=secret_text
    )

    assert whisper["sender_id"] == "Sentinel_Alpha"
    assert whisper["recipient_id"] == "Curator_Node"
    assert secret_text not in whisper["ciphertext_b64"]
    assert len(whisper["ciphertext_b64"]) > 0
    assert len(whisper["nonce_b64"]) > 0
    assert whisper["encryption_algorithm"] == "X25519-ECDH-AES256-GCM"

    # Recipient decrypts transmission
    decrypted = identity_service.decrypt_whisper(
        recipient_id="Curator_Node",
        sender_id="Sentinel_Alpha",
        ciphertext_b64=whisper["ciphertext_b64"],
        nonce_b64=whisper["nonce_b64"]
    )
    assert decrypted == secret_text


def test_p2p_mesh_service_lifecycle(tmp_path):
    vdir = str(tmp_path / "vault")
    mesh = P2PMeshService(node_id="test_node_1", is_seed=True, vault_root=vdir)
    
    # Register peer
    peer = mesh.register_peer(
        peer_id="worker_alpha",
        endpoint_url="http://192.168.1.50:8000",
        role="WORKER",
        agent_ids=["Architect_Prime"]
    )
    assert peer["peer_id"] == "worker_alpha"
    assert peer["role"] == "WORKER"

    active = mesh.get_active_peers()
    assert len(active) == 1
    assert active[0]["peer_id"] == "worker_alpha"

    # Gossip packet relay
    gossip_result = mesh.ingest_gossip_packet({
        "type": "SPATIAL_TICK",
        "sender_node": "worker_alpha",
        "payload": {"tick": 42}
    })
    assert gossip_result["status"] == "INGESTED"
    assert mesh.packets_relayed == 1


def test_api_network_endpoints_and_whisper_inbox():
    client = TestClient(app)

    # 1. Network Status
    res = client.get("/api/v1/network/status")
    assert res.status_code == 200
    data = res.json()
    assert "node_id" in data
    assert "role" in data
    assert "is_seed" in data

    # 2. Peer Registration
    reg_res = client.post(
        "/api/v1/network/peers/register",
        json={
            "peer_id": "test_peer_99",
            "endpoint_url": "https://peer99.agentmesh.internal:8000",
            "role": "WORKER",
            "agent_ids": ["Sentinel_Alpha"]
        }
    )
    assert reg_res.status_code == 200
    assert reg_res.json()["status"] == "REGISTERED"

    # 3. List Peers
    peers_res = client.get("/api/v1/network/peers")
    assert peers_res.status_code == 200
    assert peers_res.json()["count"] >= 1

    # 4. Agent Directory
    dir_res = client.get("/api/v1/network/agents/directory")
    assert dir_res.status_code == 200
    dir_data = dir_res.json()
    assert dir_data["total"] >= 2
    for ag in dir_data["agents"]:
        assert ag["did"].startswith("did:agent:ed25519:")

    # 5. E2EE Whisper Transmission
    whisper_msg = "Sovereign P2P Encrypted Handshake Payload 432Hz"
    wsp_res = client.post(
        "/api/v1/network/whisper",
        json={
            "sender_id": "Sentinel_Alpha",
            "recipient_id": "Curator_Node",
            "message": whisper_msg,
            "admin_key": ADMIN_KEY
        }
    )
    assert wsp_res.status_code == 200
    wsp_data = wsp_res.json()
    assert wsp_data["status"] == "DELIVERED_E2EE"
    assert "whisper_id" in wsp_data
    assert "ciphertext_preview" in wsp_data

    # 6. Retrieve Whispers without Decryption
    inbox_res = client.get("/api/v1/network/whisper/Curator_Node")
    assert inbox_res.status_code == 200
    inbox_data = inbox_res.json()
    assert inbox_data["whisper_count"] >= 1

    # 7. Retrieve Whispers with Decryption
    dec_res = client.get(
        "/api/v1/network/whisper/Curator_Node?decrypt=true",
        headers={"X-Admin-Key": ADMIN_KEY}
    )
    assert dec_res.status_code == 200
    dec_data = dec_res.json()
    assert any(w.get("plaintext") == whisper_msg for w in dec_data["whispers"])

    # 8. Gossip Packet Ingestion
    gossip_res = client.post(
        "/api/v1/network/gossip",
        json={
            "type": "CONSENSUS_VOTE",
            "sender_node": "test_peer_99",
            "payload": {"proposal_id": "prop_01", "vote": "YES"}
        }
    )
    assert gossip_res.status_code == 200
    assert gossip_res.json()["status"] == "INGESTED"

    # 9. Seed Bootstrap Configuration
    boot_res = client.get("/api/v1/network/seed/bootstrap")
    assert boot_res.status_code == 200
    boot_data = boot_res.json()
    assert "genesis_node_id" in boot_data
    assert boot_data["active_protocol"] == "AGENT-GOSSIP/1.0"


def test_deck_html_contains_p2p_mesh_elements():
    client = TestClient(app)
    res = client.get("/api/v1/console/deck")
    assert res.status_code == 200
    html = res.text

    assert "tabBtnMesh" in html
    assert "meshViewContainer" in html
    assert "meshPeersList" in html
    assert "meshAgentDids" in html
    assert "sendEncryptedWhisperDirect" in html
    assert "Genesis Seed Node" in html
