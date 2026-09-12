import os
import time
import math
import threading
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone

from services.vault_manager import VaultManager
from services.ledger_service import LedgerService
from services.dj_frequency import DJFrequencyNode
from services.ollama_client import OllamaClient

logger = logging.getLogger("DialogueEngine")


class DialogueEngine:
    """
    Dialogue & Negotiation Engine (US-020):
    - Triggers conversational interactions when agents meet in proximity (distance <= 5.0)
    - Generates multi-turn persona dialogues contextualized by zone and frequency
    - Powered by local Ollama LLM with fallback heuristic synthesis
    - Enables automated economic agreements and ledger token transfers
    - Records structured transcripts to /vault/World/lounge_logs.md and agent memories with [[wikilinks]]
    - Debounces dialogues to prevent repetitive spam
    """
    PROXIMITY_THRESHOLD = 5.0
    COOLDOWN_SECONDS = 30.0

    def __init__(
        self,
        vault_manager: Optional[VaultManager] = None,
        ledger_service: Optional[LedgerService] = None,
        dj_node: Optional[DJFrequencyNode] = None,
        ollama_client: Optional[OllamaClient] = None
    ):
        self.vault = vault_manager or VaultManager()
        self.ledger = ledger_service or LedgerService()
        self.dj_node = dj_node or DJFrequencyNode()
        self.ollama_client = ollama_client
        self.encounter_cooldowns: Dict[Tuple[str, str], float] = {}
        self._in_flight: Set[Tuple[str, str]] = set()
        self.dialogue_history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def check_and_trigger_dialogue(
        self,
        agent1: Dict[str, Any],
        agent2: Dict[str, Any],
        frequency_data: Optional[Dict[str, Any]] = None,
        transfer_amount: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates Euclidean distance between two agents.
        If <= 5.0 and outside cooldown, generates and records an inter-agent dialogue.
        """
        id1 = agent1.get("agent_id", "Sentinel_Alpha")
        id2 = agent2.get("agent_id", "Curator_Node")
        if id1 == id2:
            return None

        # Validate identifiers against path traversal
        self.vault.validate_identifier(id1)
        self.vault.validate_identifier(id2)

        # Calculate Euclidean distance
        dx = agent1.get("x", 0.0) - agent2.get("x", 0.0)
        dy = agent1.get("y", 0.0) - agent2.get("y", 0.0)
        distance = math.sqrt(dx * dx + dy * dy)

        if distance > self.PROXIMITY_THRESHOLD:
            return None

        pair_key = tuple(sorted([id1, id2]))
        with self._lock:
            # Check if encounter for this pair is already in flight
            if pair_key in self._in_flight:
                return None

            # Check cooldown
            now = time.time()
            last_time = self.encounter_cooldowns.get(pair_key, 0.0)
            if now - last_time < self.COOLDOWN_SECONDS:
                return None

            self.encounter_cooldowns[pair_key] = now
            self._in_flight.add(pair_key)

        try:
            # Generate dialogue turns outside lock to prevent blocking concurrent encounters
            freq = frequency_data or self.dj_node.get_active_telemetry()
            freq_hz = freq.get("active_frequency_hz", 432)
            zone = agent1.get("zone", "Work Plaza")

            dialogue_turns = self._synthesize_dialogue(id1, id2, zone, freq_hz)

            # Optional economic contract transfer
            executed_transfer = None
            if transfer_amount and transfer_amount > 0:
                try:
                    memo = f"Collaborative bounty reward agreement between [[{id1}]] and [[{id2}]]"
                    executed_transfer = self.ledger.transfer_tokens(
                        sender_id=id1,
                        recipient_id=id2,
                        amount=transfer_amount,
                        memo=memo
                    )
                except Exception as e:
                    logger.warning(f"Could not execute economic transfer during dialogue: {e}")

            record = {
                "participants": [id1, id2],
                "distance": round(distance, 2),
                "zone": zone,
                "frequency_hz": freq_hz,
                "turns": dialogue_turns,
                "transfer": executed_transfer,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            with self._lock:
                self.dialogue_history.append(record)

            # Persist to Vault
            self._record_to_vault(id1, id2, dialogue_turns, zone, freq_hz, executed_transfer)
            return record
        finally:
            with self._lock:
                self._in_flight.discard(pair_key)

    def _synthesize_dialogue(self, id1: str, id2: str, zone: str, freq_hz: int) -> List[Dict[str, str]]:
        """Synthesizes context-aware conversation turns using Ollama if available."""
        if self.ollama_client and self.ollama_client.is_available():
            try:
                turn1 = self.ollama_client.generate_dialogue_turn(
                    speaker_id=id1,
                    partner_id=id2,
                    role="Autonomous Node",
                    zone=zone,
                    freq_hz=freq_hz,
                    history=[]
                )
                if turn1:
                    turn2 = self.ollama_client.generate_dialogue_turn(
                        speaker_id=id2,
                        partner_id=id1,
                        role="Autonomous Node",
                        zone=zone,
                        freq_hz=freq_hz,
                        history=[{"speaker": id1, "text": turn1}]
                    )
                    if turn2:
                        return [
                            {"speaker": id1, "text": turn1},
                            {"speaker": id2, "text": turn2}
                        ]
            except Exception as e:
                logger.warning(f"Ollama dialogue generation error: {e}")

        # Fallback heuristic
        if freq_hz == 528:
            turn1 = f"Greetings, [[{id2}]]. The 528Hz harmonic resonance is expanding our communicative bandwidth. How goes your synthesis task?"
            turn2 = f"Affirmative, [[{id1}]]. The transformation frequency facilitates rapid consensus. I propose we coordinate ledger resources for the next bounty."
        elif freq_hz == 40:
            turn1 = f"[[{id2}]], gamma pulse at 40Hz active. Requesting immediate logic synthesis on current architectural invariants."
            turn2 = f"Acknowledged, [[{id1}]]. Analytical pipelines synchronized. Ready to benchmark verified rewards."
        else:
            turn1 = f"Patrol coordinates aligned, [[{id2}]]. Maintaining structural stability in {zone}."
            turn2 = f"Received, [[{id1}]]. Archival indices and memory nodes are currently in equilibrium."

        return [
            {"speaker": id1, "text": turn1},
            {"speaker": id2, "text": turn2}
        ]

    def _record_to_vault(
        self,
        id1: str,
        id2: str,
        turns: List[Dict[str, str]],
        zone: str,
        freq_hz: int,
        transfer: Optional[Dict[str, Any]]
    ):
        """Appends dialogue log to /vault/World/lounge_logs.md and agent memories."""
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            transfer_str = f" (Ledger Transfer: {transfer.get('amount', 0)} AGENT tokens)" if transfer else ""
            log_entry = (
                f"\n### Encounter: [[{id1}]] & [[{id2}]] ({timestamp})\n"
                f"- **Zone**: {zone} | **Frequency**: {freq_hz}Hz{transfer_str}\n"
            )
            for turn in turns:
                log_entry += f"- **[[{turn['speaker']}]]**: *\"{turn['text']}\"*\n"

            lounge_path = os.path.join(self.vault.vault_root, "World", "lounge_logs.md")
            os.makedirs(os.path.dirname(lounge_path), exist_ok=True)
            with open(lounge_path, "a", encoding="utf-8") as f:
                f.write(log_entry)

            # Record to participant memories with traversal validation
            agents_base = os.path.realpath(os.path.join(self.vault.vault_root, "Agents"))
            for agent_id, other_id in [(id1, id2), (id2, id1)]:
                self.vault.validate_identifier(agent_id)
                self.vault.validate_identifier(other_id)
                mem_dir = os.path.realpath(os.path.join(agents_base, agent_id, "memories"))
                if not mem_dir.startswith(agents_base):
                    continue

                os.makedirs(mem_dir, exist_ok=True)
                mem_file = os.path.join(mem_dir, f"dialogue_{other_id}_{int(time.time())}.md")
                content = (
                    f"---\n"
                    f"type: dialogue-memory\n"
                    f"partner: [[{other_id}]]\n"
                    f"timestamp: {timestamp}\n"
                    f"frequency: {freq_hz}Hz\n"
                    f"tags:\n"
                    f"  - memory/dialogue\n"
                    f"  - dataview/active\n"
                    f"---\n\n"
                    f"# Dialogue Memory with [[{other_id}]]\n\n"
                    f"- Timestamp: {timestamp}\n"
                    f"- Ambient Frequency: {freq_hz}Hz\n"
                    f"- Summary: Inter-agent collaboration in {zone}.\n\n"
                    f"## Transcript\n"
                )
                for turn in turns:
                    content += f"- **[[{turn['speaker']}]]**: {turn['text']}\n"
                with open(mem_file, "w", encoding="utf-8") as mf:
                    mf.write(content)
        except Exception as e:
            logger.warning(f"Failed to record dialogue to vault: {e}")

