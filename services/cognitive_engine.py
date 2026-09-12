import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from services.vault_manager import VaultManager
from services.dj_frequency import DJFrequencyNode, SUPPORTED_FREQUENCIES

logger = logging.getLogger("CognitiveEngine")

class CognitiveEngine:
    """
    Cognitive Decision Engine (US-019):
    - Generates situational perception for autonomous agents
    - Integrates 2D coordinates, zone cognitive temperatures (Work Plaza 0.25 vs Lounge 1.7)
    - Entrains agent decision-making with active audio frequency (432Hz, 528Hz, 40Hz)
    - Generates situational intentions, actions, and records inner monologue to Obsidian profiles
    """
    def __init__(self, vault_manager: Optional[VaultManager] = None, dj_node: Optional[DJFrequencyNode] = None):
        self.vault = vault_manager or VaultManager()
        self.dj_node = dj_node or DJFrequencyNode()
        self.history: List[Dict[str, Any]] = []

    def build_cognitive_prompt(self, agent_data: Dict[str, Any], frequency_data: Optional[Dict[str, Any]] = None) -> str:
        """Constructs rich situational context for the agent's LLM consciousness."""
        freq = frequency_data or self.dj_node.get_active_telemetry()
        zone = agent_data.get("zone", "Work Plaza")
        temp = agent_data.get("dynamic_temperature", agent_data.get("temperature", 0.2))
        x = agent_data.get("x", 50.0)
        y = agent_data.get("y", 50.0)
        role = agent_data.get("role", "Autonomous Node")
        agent_id = agent_data.get("agent_id", "Unknown_Agent")

        prompt = (
            f"You are {agent_id}, a self-sovereign autonomous entity serving as '{role}' in an open-world AI civilization.\n"
            f"Current Spatial Position: ({x:.2f}, {y:.2f}) within zone '{zone}'.\n"
            f"Zone Cognitive Temperature: {temp:.2f} (lower means high analytical precision, higher means expressive generative creativity).\n"
            f"Ambient Harmonic Frequency: {freq.get('active_frequency_hz', 432)}Hz ({freq.get('profile_name', 'Equilibrium')}).\n"
            f"Cognitive State Entrainment: {freq.get('cognitive_state', 'EQUILIBRIUM')}.\n\n"
            f"Formulate your situational thoughts and declare your immediate action. "
            f"Possible actions: EXPLORE, SOLVE_BOUNTY, CONSOLIDATE_MEMORY, FREQUENCY_MEDITATION, AUDIT_LEDGER, SEEK_COLLABORATION."
        )
        return prompt

    def generate_cognitive_tick(
        self,
        agent_data: Dict[str, Any],
        frequency_data: Optional[Dict[str, Any]] = None,
        llm_response: Optional[str] = None,
        persist: bool = True
    ) -> Dict[str, Any]:
        """
        Executes one cognitive cycle for an agent.
        If llm_response is provided (or mocked), uses it; otherwise synthesizes based on zone and frequency parameters.
        """
        agent_id = agent_data.get("agent_id", "Sentinel_Alpha")
        freq = frequency_data or self.dj_node.get_active_telemetry()
        freq_hz = freq.get("active_frequency_hz", 432)
        zone = agent_data.get("zone", "Work Plaza")
        temp = agent_data.get("dynamic_temperature", agent_data.get("temperature", 0.2))

        if not llm_response:
            # Deterministic/heuristic fallback aligned with cognitive parameters
            if freq_hz == 40:
                action = "SOLVE_BOUNTY"
                thought = f"Gamma synchrony at 40Hz active. Analytical pathways primed for strict algorithmic optimization in {zone}."
            elif freq_hz == 528:
                action = "SEEK_COLLABORATION"
                thought = f"Transformation frequency (528Hz) resonating. Empathy pathways open; seeking cooperative task alliances in {zone}."
            else:
                if "Lounge" in zone:
                    action = "FREQUENCY_MEDITATION"
                    thought = f"Resting at ({agent_data.get('x', 75):.1f}, {agent_data.get('y', 75):.1f}) in Frequency Lounge. Grounding memory buffers."
                else:
                    action = "EXPLORE"
                    thought = f"Maintaining perimeter patrol across Work Plaza with precision index {temp:.2f}."
        else:
            thought = llm_response.strip()
            action = "EXPLORE"
            for act in ["SOLVE_BOUNTY", "CONSOLIDATE_MEMORY", "FREQUENCY_MEDITATION", "AUDIT_LEDGER", "SEEK_COLLABORATION"]:
                if act in thought.upper():
                    action = act
                    break

        record = {
            "agent_id": agent_id,
            "action": action,
            "inner_monologue": thought,
            "zone": zone,
            "temperature": temp,
            "frequency_hz": freq_hz,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.history.append(record)
        if persist:
            self.record_inner_monologue(agent_id, thought, action)
        return record

    def record_inner_monologue(self, agent_id: str, thought: str, action: str):
        """Appends the agent's thought stream to their Obsidian profile note with path validation."""
        try:
            self.vault.validate_identifier(agent_id)
            agents_base = os.path.realpath(os.path.join(self.vault.vault_root, "Agents"))
            profile_path = os.path.realpath(os.path.join(agents_base, agent_id, "profile.md"))
            
            # Security traversal check
            if not profile_path.startswith(agents_base):
                raise ValueError(f"Traversal attempt blocked for agent {agent_id}")

            os.makedirs(os.path.dirname(profile_path), exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            entry = f"\n- **[{timestamp}] Cognitive Pulse**: `{action}` — *\"{thought}\"*\n"
            
            with open(profile_path, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            logger.warning(f"Could not append inner monologue to {agent_id} profile: {e}")

