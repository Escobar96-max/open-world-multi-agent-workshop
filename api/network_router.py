import os
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from services.agent_identity import AgentIdentityService
from services.p2p_mesh import P2PMeshService
from services.console_c2 import ConsoleC2Service, ConsoleSecurityError
from services.vault_manager import VaultManager

router = APIRouter(prefix="/api/v1/network", tags=["P2P Mesh Network & Sovereign Privacy"])

vault_mgr = VaultManager()
identity_service = AgentIdentityService(vault_root=vault_mgr.vault_root)
p2p_service = P2PMeshService(vault_root=vault_mgr.vault_root, identity_service=identity_service)
console_service = ConsoleC2Service(vault_manager=vault_mgr)


class PeerRegisterRequest(BaseModel):
    peer_id: str = Field(..., description="Unique remote peer node ID")
    endpoint_url: str = Field(..., description="Remote peer base HTTP/WS endpoint")
    role: Optional[str] = Field("PEER", description="Node role: SEED, WORKER, or PEER")
    agent_ids: Optional[List[str]] = Field(default_factory=list, description="List of local agents managed by this peer")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional node telemetry")


class WhisperSendRequest(BaseModel):
    sender_id: str = Field(..., description="Sender agent ID")
    recipient_id: str = Field(..., description="Recipient agent ID")
    message: str = Field(..., description="Plaintext confidential whisper to encrypt E2EE")
    admin_key: Optional[str] = Field(None, description="Admin authorization key")


class GossipPacketRequest(BaseModel):
    type: str = Field(..., description="Packet type: SPATIAL_TICK, CONSENSUS_VOTE, STATE_SYNC")
    sender_node: str = Field(..., description="Sending peer node ID")
    payload: Dict[str, Any] = Field(..., description="Gossip payload")
    signature: Optional[str] = Field(None, description="Cryptographic Ed25519 signature")


@router.get("/status", summary="P2P Mesh Network Telemetry")
async def get_network_status():
    """Returns Genesis node status, active peer counts, sovereign agent count, and uptime."""
    return p2p_service.get_network_telemetry()


@router.post("/peers/register", summary="Register Remote Peer Node")
async def register_mesh_peer(req: PeerRegisterRequest):
    """Registers a peer into the local AgentWorld mesh table."""
    peer = p2p_service.register_peer(
        peer_id=req.peer_id,
        endpoint_url=req.endpoint_url,
        role=req.role or "PEER",
        agent_ids=req.agent_ids,
        metadata=req.metadata
    )
    return {
        "status": "REGISTERED",
        "peer": peer,
        "local_node_id": p2p_service.node_id,
        "is_seed": p2p_service.is_seed
    }


@router.get("/peers", summary="List Active Mesh Peers")
async def list_mesh_peers():
    """Lists all currently active P2P peers discovered by this node."""
    peers = p2p_service.get_active_peers()
    return {
        "count": len(peers),
        "peers": peers
    }


@router.get("/agents/directory", summary="Sovereign Agent Cryptographic Directory")
async def get_agent_directory():
    """Returns all sovereign agents with their DIDs and public keys."""
    # Ensure known agents are initialized
    known_agents = ["Sentinel_Alpha", "Curator_Node", "Architect_Prime", "Dr._Aris", "A.E.G.I.S.", "Vector-09"]
    directory = []
    for ag in known_agents:
        info = identity_service.get_or_create_identity(ag)
        directory.append(info)
    return {
        "total": len(directory),
        "agents": directory
    }


@router.post("/whisper", summary="Send End-to-End Encrypted (E2EE) Whisper")
async def send_agent_whisper(
    req: WhisperSendRequest,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
):
    """
    Encrypts a confidential message using X25519-ECDH + AES-256-GCM
    and stores it in the recipient agent's private inbox.
    """
    admin_key = x_admin_key or req.admin_key
    try:
        console_service.verify_admin_key(admin_key)
    except ConsoleSecurityError as e:
        raise HTTPException(status_code=401, detail=str(e))

    vault_mgr.validate_identifier(req.sender_id)
    vault_mgr.validate_identifier(req.recipient_id)

    # 1. Encrypt whisper with sender & recipient keys
    encrypted_packet = identity_service.encrypt_whisper(
        sender_id=req.sender_id,
        recipient_id=req.recipient_id,
        plaintext=req.message
    )

    # 2. Store encrypted transmission in recipient inbox
    stored_record = p2p_service.store_whisper_transmission(encrypted_packet)

    return {
        "status": "DELIVERED_E2EE",
        "whisper_id": stored_record["whisper_id"],
        "sender_id": req.sender_id,
        "recipient_id": req.recipient_id,
        "sender_did": encrypted_packet["sender_did"],
        "recipient_did": encrypted_packet["recipient_did"],
        "ciphertext_preview": encrypted_packet["ciphertext_b64"][:24] + "...",
        "encryption": encrypted_packet["encryption_algorithm"]
    }


@router.get("/whisper/{agent_id}", summary="Retrieve Encrypted Agent Whispers")
async def get_agent_whispers(
    agent_id: str,
    decrypt: bool = Query(False, description="Decrypt whispers if authorized"),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    admin_key: Optional[str] = Query(None, description="Admin key query parameter fallback")
):
    """Retrieves all whispers in an agent's inbox, with optional E2EE decryption."""
    vault_mgr.validate_identifier(agent_id)
    key = x_admin_key or admin_key

    whispers = p2p_service.get_agent_whispers(agent_id)

    if decrypt:
        try:
            console_service.verify_admin_key(key)
        except ConsoleSecurityError as e:
            raise HTTPException(status_code=401, detail=f"Decryption requires valid admin authorization: {str(e)}")

        decrypted_list = []
        for w in whispers:
            w_copy = dict(w)
            try:
                plaintext = identity_service.decrypt_whisper(
                    recipient_id=agent_id,
                    sender_id=w["sender_id"],
                    ciphertext_b64=w["ciphertext_b64"],
                    nonce_b64=w["nonce_b64"]
                )
                w_copy["plaintext"] = plaintext
                w_copy["decrypted"] = True
            except Exception as e:
                w_copy["decrypted"] = False
                w_copy["error"] = str(e)
            decrypted_list.append(w_copy)
        return {
            "agent_id": agent_id,
            "whisper_count": len(decrypted_list),
            "whispers": decrypted_list
        }

    return {
        "agent_id": agent_id,
        "whisper_count": len(whispers),
        "whispers": whispers
    }


@router.post("/gossip", summary="Broadcast or Ingest Mesh Gossip Packet")
async def process_gossip(packet: GossipPacketRequest):
    """Processes an incoming P2P gossip packet and relays across local mesh state."""
    result = p2p_service.ingest_gossip_packet(packet.model_dump())
    return result


@router.get("/seed/bootstrap", summary="Generate P2P Seed Bootstrap Configuration")
async def get_seed_bootstrap():
    """Returns genesis seed configuration packet to allow secondary nodes to bootstrap."""
    telemetry = p2p_service.get_network_telemetry()
    return {
        "genesis_node_id": telemetry["node_id"],
        "is_genesis_seed": telemetry["is_seed"],
        "recommended_bootstrap_endpoints": [
            "http://localhost:8000/api/v1/network",
            "https://mechanism-suffering-absolute-atm.trycloudflare.com/api/v1/network"
        ],
        "active_protocol": "AGENT-GOSSIP/1.0",
        "mesh_capabilities": ["E2EE_WHISPER", "CRDT_MEMORY", "SPATIAL_GOSSIP", "DID_ED25519"]
    }
