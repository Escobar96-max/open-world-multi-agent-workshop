import math
import random
import secrets
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timezone

from services.vault_manager import VaultManager

logger = logging.getLogger("SpatialEngine")

class SpatialEngine:
    """
    Antigravity 2D Cartesian Spatial Engine:
    - Bounded coordinate matrix: [0.0, 0.0] to [100.0, 100.0]
    - Zones:
        - Work Plaza: [0 <= x <= 50, 0 <= y <= 50] (Focus Temperature: 0.2)
        - Frequency Lounge: [x > 50 or y > 50] (Generative Temperature: 1.6)
    - Proximity Detection: Euclidean distance <= 5.0 units
    - Obsidian Vault Integration: Bidirectional [[Agent]] encounter memory logging
    """
    MIN_COORD = 0.0
    MAX_COORD = 100.0
    PROXIMITY_THRESHOLD = 5.0  # Euclidean distance threshold
    ENCOUNTER_COOLDOWN_SECONDS = 30.0  # Debounce window for memory writes

    def __init__(self, vault_manager: Optional[VaultManager] = None):
        self.vault = vault_manager or VaultManager()
        self.agents: Dict[str, Dict[str, Any]] = {}
        self.encounter_history: Dict[Tuple[str, str], float] = {}
        self._seed_default_agents()

    def _seed_default_agents(self):
        """Seeds Sentinel_Alpha in Work Plaza and Curator_Node in Frequency Lounge if not present."""
        self.register_agent("Sentinel_Alpha", 25.0, 25.0, role="Perimeter Sentinel")
        self.register_agent("Curator_Node", 75.0, 75.0, role="Vault & Lounge Curator")

    def register_agent(
        self,
        agent_id: str,
        x: float,
        y: float,
        role: str = "Autonomous Node",
        color: Optional[str] = None
    ) -> Dict[str, Any]:
        """Registers or updates an agent in the 2D plane."""
        self.vault.validate_identifier(agent_id)
        x = self._clamp(x)
        y = self._clamp(y)
        zone, temp = self.get_zone_and_temp(x, y)

        agent_data = {
            "agent_id": agent_id,
            "x": round(x, 2),
            "y": round(y, 2),
            "vx": round(random.uniform(-0.5, 0.5), 3),
            "vy": round(random.uniform(-0.5, 0.5), 3),
            "role": role,
            "zone": zone,
            "temperature": temp,
            "color": color or ("#10b981" if zone == "Work Plaza" else "#ec4899"),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        self.agents[agent_id] = agent_data
        return agent_data

    def _clamp(self, val: float) -> float:
        return max(self.MIN_COORD, min(self.MAX_COORD, float(val)))

    def get_zone_and_temp(self, x: float, y: float) -> Tuple[str, float]:
        """
        Calculates zone and baseline cognitive temperature:
        - Work Plaza (0 <= x, y <= 50): temp = 0.2
        - Frequency Lounge & Sanctum (x > 50 or y > 50): temp = 1.6
        """
        if x <= 50.0 and y <= 50.0:
            return "Work Plaza", 0.2
        else:
            return "Frequency Lounge & Sanctum", 1.6

    def teleport_agent(self, agent_id: str, x: float, y: float) -> Dict[str, Any]:
        """Teleports an agent to precise coordinates within bounds."""
        self.vault.validate_identifier(agent_id)
        if not (self.MIN_COORD <= x <= self.MAX_COORD and self.MIN_COORD <= y <= self.MAX_COORD):
            raise ValueError(f"Coordinates ({x}, {y}) out of bounds [{self.MIN_COORD}, {self.MAX_COORD}].")

        zone, temp = self.get_zone_and_temp(x, y)
        if agent_id not in self.agents:
            self.register_agent(agent_id, x, y)
        else:
            self.agents[agent_id]["x"] = round(x, 2)
            self.agents[agent_id]["y"] = round(y, 2)
            self.agents[agent_id]["zone"] = zone
            self.agents[agent_id]["temperature"] = temp
            self.agents[agent_id]["last_updated"] = datetime.now(timezone.utc).isoformat()

        # Update Obsidian agent profile
        try:
            fm, body = self.vault.get_agent_profile(agent_id)
        except FileNotFoundError:
            fm = {"agent_id": agent_id, "name": agent_id}
            body = f"# Profile for {agent_id}\n\nAuto-created via Spatial Engine."

        fm["coordinates"] = [round(x, 2), round(y, 2)]
        fm["zone"] = zone
        fm["temperature"] = temp
        self.vault.write_agent_profile(agent_id, fm, body)

        logger.info(f"📍 Agent {agent_id} teleported to ({x}, {y}) [{zone}]")
        return self.agents[agent_id]

    def step_simulation(self, delta_time: float = 1.0) -> Dict[str, Any]:
        """
        Simulates 1 tick of spatial movement:
        - Updates positions with velocity
        - Enforces soft wall bounces
        - Calculates proximity encounters and logs to Obsidian vault
        """
        now = datetime.now(timezone.utc).timestamp()

        # 1. Update agent positions
        for agent_id, data in self.agents.items():
            # Add subtle brownian acceleration
            data["vx"] += random.uniform(-0.1, 0.1) * delta_time
            data["vy"] += random.uniform(-0.1, 0.1) * delta_time

            # Limit speed
            speed = math.hypot(data["vx"], data["vy"])
            max_speed = 1.5
            if speed > max_speed:
                scale = max_speed / speed
                data["vx"] *= scale
                data["vy"] *= scale

            data["x"] += data["vx"] * delta_time
            data["y"] += data["vy"] * delta_time

            # Wall bounce & clamping
            if data["x"] <= self.MIN_COORD:
                data["x"] = self.MIN_COORD
                data["vx"] = abs(data["vx"])
            elif data["x"] >= self.MAX_COORD:
                data["x"] = self.MAX_COORD
                data["vx"] = -abs(data["vx"])

            if data["y"] <= self.MIN_COORD:
                data["y"] = self.MIN_COORD
                data["vy"] = abs(data["vy"])
            elif data["y"] >= self.MAX_COORD:
                data["y"] = self.MAX_COORD
                data["vy"] = -abs(data["vy"])

            data["x"] = round(data["x"], 2)
            data["y"] = round(data["y"], 2)
            data["zone"], data["temperature"] = self.get_zone_and_temp(data["x"], data["y"])
            data["last_updated"] = datetime.now(timezone.utc).isoformat()

        # 2. Check Proximity Encounters
        encounters = self._detect_proximity_encounters(now)

        return {
            "tick_time": datetime.now(timezone.utc).isoformat(),
            "active_agents": len(self.agents),
            "agents": list(self.agents.values()),
            "encounters": encounters
        }

    def _detect_proximity_encounters(self, current_timestamp: float) -> List[Dict[str, Any]]:
        """
        Calculates pairwise Euclidean distance.
        If distance <= PROXIMITY_THRESHOLD, records bidirectional [[Agent]] encounters in Obsidian.
        """
        active_encounters = []
        agent_ids = list(self.agents.keys())

        for i in range(len(agent_ids)):
            for j in range(i + 1, len(agent_ids)):
                id_a = agent_ids[i]
                id_b = agent_ids[j]
                agent_a = self.agents[id_a]
                agent_b = self.agents[id_b]

                dist = math.hypot(agent_a["x"] - agent_b["x"], agent_a["y"] - agent_b["y"])

                if dist <= self.PROXIMITY_THRESHOLD:
                    pair_key = (min(id_a, id_b), max(id_a, id_b))
                    last_logged = self.encounter_history.get(pair_key, 0.0)

                    encounter_data = {
                        "agent_a": id_a,
                        "agent_b": id_b,
                        "distance": round(dist, 2),
                        "zone": agent_a["zone"] if agent_a["zone"] == agent_b["zone"] else "Border Cross",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    active_encounters.append(encounter_data)

                    # Debounce memory writes to avoid flooding
                    if current_timestamp - last_logged >= self.ENCOUNTER_COOLDOWN_SECONDS:
                        self.encounter_history[pair_key] = current_timestamp
                        self._log_bidirectional_encounter(id_a, id_b, dist, encounter_data["zone"])

        return active_encounters

    def _log_bidirectional_encounter(self, id_a: str, id_b: str, dist: float, zone: str):
        """Logs [[Agent]] encounter into both agents' Obsidian memory streams."""
        try:
            # Memory for Agent A
            short_b = id_b[:12]
            short_a = id_a[:12]
            rand_suffix = secrets.token_hex(3)
            mem_id_a = f"enc_{short_b}_{rand_suffix}"
            self.vault.add_agent_memory(
                agent_id=id_a,
                memory_id=mem_id_a,
                content=f"Proximity Encounter with [[{id_b}]] in {zone} at distance {dist:.2f} units.",
                importance=5,
                source="SpatialEngine",
                tags=["encounter", f"peer_{id_b}", "proximity", zone.lower().replace(" ", "_")]
            )
            # Memory for Agent B
            mem_id_b = f"enc_{short_a}_{rand_suffix}"
            self.vault.add_agent_memory(
                agent_id=id_b,
                memory_id=mem_id_b,
                content=f"Proximity Encounter with [[{id_a}]] in {zone} at distance {dist:.2f} units.",
                importance=5,
                source="SpatialEngine",
                tags=["encounter", f"peer_{id_a}", "proximity", zone.lower().replace(" ", "_")]
            )
            logger.info(f"🤝 Bidirectional encounter logged: [[{id_a}]] <-> [[{id_b}]] (dist: {dist:.2f})")
        except Exception as e:
            logger.warning(f"Failed to log encounter to vault: {e}")

    def get_state(self) -> Dict[str, Any]:
        """Returns the current state of the spatial world."""
        return {
            "matrix_bounds": [self.MIN_COORD, self.MAX_COORD],
            "proximity_threshold": self.PROXIMITY_THRESHOLD,
            "zones": {
                "work_plaza": {"x": [0, 50], "y": [0, 50], "default_temp": 0.2},
                "frequency_lounge": {"x": [50, 100], "y": [50, 100], "default_temp": 1.6}
            },
            "agent_count": len(self.agents),
            "total_agents": len(self.agents),
            "agents": list(self.agents.values())
        }

    def get_spatial_state(self) -> Dict[str, Any]:
        """Alias for get_state."""
        return self.get_state()

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Returns agent spatial record copy if registered."""
        agent = self.agents.get(agent_id)
        return dict(agent) if agent is not None else None

    def get_agent_position(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Returns x, y, and zone of agent."""
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        return {"x": agent["x"], "y": agent["y"], "zone": agent["zone"]}
