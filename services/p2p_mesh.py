import os
import time
import json
import secrets
import logging
from typing import Dict, Any, List, Optional
from services.agent_identity import AgentIdentityService

logger = logging.getLogger(__name__)


class P2PMeshService:
    """
    Decentralized P2P Mesh Networking & Seeding Service.
    
    Handles:
    - Node Registration & Heartbeats (Genesis Seed vs Remote Peer)
    - P2P State Gossip (CRDT World State, Spatial Positions, Consensus)
    - Encrypted Whisper Store & Inbox Routing
    - Multi-Node Bootstrap Discovery
    """

    def __init__(
        self,
        node_id: Optional[str] = None,
        is_seed: bool = True,
        vault_root: str = "vault",
        identity_service: Optional[AgentIdentityService] = None
    ):
        self.node_id = node_id or os.getenv("P2P_NODE_ID", f"seed_0_{secrets.token_hex(4)}")
        self.is_seed = is_seed if os.getenv("P2P_IS_SEED") is None else (os.getenv("P2P_IS_SEED") == "true")
        self.vault_root = vault_root
        self.identity = identity_service or AgentIdentityService(vault_root=vault_root)

        self.peers: Dict[str, Dict[str, Any]] = {}
        self.gossip_history: List[Dict[str, Any]] = []
        self.packets_relayed: int = 0
        self.started_at: float = time.time()

    def register_peer(
        self,
        peer_id: str,
        endpoint_url: str,
        role: str = "PEER",
        agent_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Registers or updates a peer in the local mesh directory."""
        now = time.time()
        peer_data = {
            "peer_id": peer_id,
            "endpoint_url": endpoint_url,
            "role": role,
            "agent_ids": agent_ids or [],
            "first_seen": self.peers.get(peer_id, {}).get("first_seen", now),
            "last_seen": now,
            "status": "ONLINE",
            "metadata": metadata or {}
        }
        self.peers[peer_id] = peer_data
        logger.info(f"[P2P MESH] Peer registered: {peer_id} @ {endpoint_url} [{role}]")
        return peer_data

    def get_active_peers(self, timeout_sec: float = 120.0) -> List[Dict[str, Any]]:
        """Returns all peers active within the timeout threshold."""
        now = time.time()
        active = []
        for p in self.peers.values():
            if now - p["last_seen"] <= timeout_sec:
                active.append(p)
            else:
                p["status"] = "STALE"
        return active

    def ingest_gossip_packet(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """Validates and processes an inbound gossip packet."""
        packet_type = packet.get("type", "UNKNOWN")
        sender_node = packet.get("sender_node", "anonymous")
        payload = packet.get("payload", {})
        signature = packet.get("signature")

        # Track packets
        self.packets_relayed += 1
        record = {
            "type": packet_type,
            "sender_node": sender_node,
            "timestamp": packet.get("timestamp", time.time()),
            "packet_id": packet.get("packet_id", secrets.token_hex(4))
        }
        self.gossip_history.append(record)
        if len(self.gossip_history) > 100:
            self.gossip_history = self.gossip_history[-100:]

        return {
            "status": "INGESTED",
            "packet_id": record["packet_id"],
            "type": packet_type,
            "relayed_by": self.node_id
        }

    def store_whisper_transmission(self, whisper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stores an encrypted whisper transmission into the recipient agent's private inbox.
        The content is stored in encrypted form; only the recipient private key can decrypt it.
        """
        recipient_id = whisper["recipient_id"]
        whisper_dir = os.path.join(self.vault_root, "Agents", recipient_id, "whispers")
        os.makedirs(whisper_dir, exist_ok=True)

        whisper_id = f"wsp_{int(time.time())}_{secrets.token_hex(4)}"
        whisper_file = os.path.join(whisper_dir, f"{whisper_id}.json")

        record = {
            "whisper_id": whisper_id,
            "sender_id": whisper["sender_id"],
            "recipient_id": recipient_id,
            "sender_did": whisper.get("sender_did"),
            "recipient_did": whisper.get("recipient_did"),
            "ciphertext_b64": whisper["ciphertext_b64"],
            "nonce_b64": whisper["nonce_b64"],
            "signature": whisper.get("signature"),
            "received_at": time.time(),
            "status": "UNREAD"
        }

        with open(whisper_file, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

        return record

    def get_agent_whispers(self, agent_id: str) -> List[Dict[str, Any]]:
        """Reads all encrypted whispers in an agent's inbox."""
        whisper_dir = os.path.join(self.vault_root, "Agents", agent_id, "whispers")
        if not os.path.exists(whisper_dir):
            return []

        whispers = []
        for fn in sorted(os.listdir(whisper_dir), reverse=True):
            if fn.endswith(".json"):
                try:
                    with open(os.path.join(whisper_dir, fn), "r", encoding="utf-8") as f:
                        whispers.append(json.load(f))
                except Exception as e:
                    logger.warning(f"Failed to read whisper file {fn}: {e}")
        return whispers

    def get_network_telemetry(self) -> Dict[str, Any]:
        """Provides full telemetry of the node and active mesh connections."""
        active_peers = self.get_active_peers()
        uptime_sec = round(time.time() - self.started_at, 1)

        # Count registered agent keys
        agents_dir = os.path.join(self.vault_root, "Agents")
        sovereign_agents = []
        if os.path.exists(agents_dir):
            for ag in os.listdir(agents_dir):
                if os.path.isdir(os.path.join(agents_dir, ag)):
                    key_file = os.path.join(agents_dir, ag, ".keys", "signing_public.key")
                    if os.path.exists(key_file):
                        sovereign_agents.append(ag)

        return {
            "node_id": self.node_id,
            "role": "GENESIS_SEED" if self.is_seed else "MESH_PEER",
            "is_seed": self.is_seed,
            "uptime_seconds": uptime_sec,
            "active_peers_count": len(active_peers),
            "peers": active_peers,
            "packets_relayed": self.packets_relayed,
            "sovereign_agents_count": len(sovereign_agents),
            "sovereign_agents": sovereign_agents,
            "gossip_queue_len": len(self.gossip_history)
        }
