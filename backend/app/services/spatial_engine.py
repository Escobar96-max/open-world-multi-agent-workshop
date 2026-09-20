"""
Antigravity 2D Spatial Engine:
Coordinates bounded [0, 100] matrix partitioned into Work Plaza (0-50, temp 0.2)
and Frequency Lounge (51-100, temp 1.6). Calculates Euclidean proximity (<= 5.0)
and logs bidirectional agent encounters.
"""

import math
import logging
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel

from app.config import settings
from app.services.vault_manager import VaultManager

logger = logging.getLogger("spatial.engine")


class SpatialAgent(BaseModel):
    id: str
    name: str
    role: str
    x: float
    y: float
    zone: str = "Work Plaza"
    temperature: float = 0.2
    status: str = "nominal"


class SpatialEngine:
    """Manages 2D coordinates, zone classification, and proximity encounters."""

    def __init__(self, vault_manager: Optional[VaultManager] = None):
        self.vault = vault_manager or VaultManager()
        self.grid_min = settings.grid_min
        self.grid_max = settings.grid_max
        self.plaza_max = settings.work_plaza_max
        self.lounge_min = settings.lounge_min
        self.proximity_threshold = settings.proximity_threshold

        self.agents: Dict[str, SpatialAgent] = {}
        self._recent_encounters: Dict[str, float] = {}
        self.tick_count = 0
        self._seed_foundation_agents()

    def _seed_foundation_agents(self):
        """Initializes foundation agents in the 2D Cartesian plane."""
        defaults = [
            ("Orion_Prime", "👑 Orion Prime", "Chief Orchestrator", 22.0, 26.0),
            ("Nova", "🌸 Nova", "Executive Assistant", 25.0, 28.0),
            ("Architect_Prime", "⚙️ Architect Prime", "Dev Loop Engine", 18.0, 32.0),
            ("Sentinel_Alpha", "🛡️ Sentinel Alpha", "Gatekeeper Defense", 12.0, 14.0),
            ("Curator_Node", "📚 Curator Node", "Vault Archival", 72.0, 74.0),
            ("DJ_Frequency", "🎵 DJ Frequency", "Lounge Host", 82.0, 84.0)
        ]
        for aid, name, role, x, y in defaults:
            zone, temp = self.classify_zone(x, y)
            self.agents[aid] = SpatialAgent(
                id=aid,
                name=name,
                role=role,
                x=x,
                y=y,
                zone=zone,
                temperature=temp
            )

    def classify_zone(self, x: float, y: float) -> Tuple[str, float]:
        """Classifies coordinates into Work Plaza or Frequency Lounge with cognitive temp."""
        if x <= self.plaza_max and y <= self.plaza_max:
            return "Work Plaza", settings.work_plaza_temp
        elif x >= self.lounge_min and y >= self.lounge_min:
            return "Frequency Lounge", settings.lounge_temp
        else:
            return "Transition Buffer", 0.8

    def clamp(self, val: float) -> float:
        return max(self.grid_min, min(self.grid_max, val))

    def update_position(self, agent_id: str, x: float, y: float) -> Dict[str, Any]:
        """Moves an agent to target coordinates, enforcing bounds."""
        if agent_id not in self.agents:
            return {"success": False, "error": f"Agent '{agent_id}' not found."}

        clamped_x = self.clamp(x)
        clamped_y = self.clamp(y)
        zone, temp = self.classify_zone(clamped_x, clamped_y)

        agent = self.agents[agent_id]
        agent.x = clamped_x
        agent.y = clamped_y
        agent.zone = zone
        agent.temperature = temp

        encounters = self.check_proximity()
        return {
            "success": True,
            "agent": agent.model_dump(),
            "encounters": encounters
        }

    def teleport(self, agent_id: str, target: str) -> Dict[str, Any]:
        """Teleports agent to 'plaza' (25, 25) or 'lounge' (75, 75)."""
        target_lower = target.lower()
        if "lounge" in target_lower:
            return self.update_position(agent_id, 75.0, 75.0)
        elif "plaza" in target_lower or "work" in target_lower:
            return self.update_position(agent_id, 25.0, 25.0)
        else:
            return {"success": False, "error": f"Unknown teleport destination '{target}'."}

    def check_proximity(self) -> List[Dict[str, Any]]:
        """Calculates pairwise Euclidean distance and returns encounters <= threshold."""
        encounters = []
        agent_list = list(self.agents.values())

        for i in range(len(agent_list)):
            for j in range(i + 1, len(agent_list)):
                a1 = agent_list[i]
                a2 = agent_list[j]

                dist = math.sqrt((a1.x - a2.x) ** 2 + (a1.y - a2.y) ** 2)
                if dist <= self.proximity_threshold:
                    encounters.append({
                        "agent_1": a1.id,
                        "agent_2": a2.id,
                        "distance": round(dist, 2),
                        "zone": a1.zone
                    })
        return encounters

    def tick(self) -> Dict[str, Any]:
        """Advances simulation state and applies subtle kinetic drift."""
        self.tick_count += 1
        # Apply tiny organic drift within bounds
        for a in self.agents.values():
            if a.zone == "Frequency Lounge":
                # Subtle relaxation wandering
                a.x = self.clamp(a.x + (math.sin(self.tick_count * 0.5) * 0.4))
                a.y = self.clamp(a.y + (math.cos(self.tick_count * 0.5) * 0.4))
            zone, temp = self.classify_zone(a.x, a.y)
            a.zone = zone
            a.temperature = temp

        encounters = self.check_proximity()
        return {
            "tick": self.tick_count,
            "agents": [a.model_dump() for a in self.agents.values()],
            "encounters": encounters
        }

    def get_state(self) -> Dict[str, Any]:
        return {
            "tick": self.tick_count,
            "grid": {"min": self.grid_min, "max": self.grid_max},
            "zones": {
                "work_plaza": {"bounds": [0, 50, 0, 50], "temp": settings.work_plaza_temp},
                "frequency_lounge": {"bounds": [51, 100, 51, 100], "temp": settings.lounge_temp}
            },
            "agents": [a.model_dump() for a in self.agents.values()]
        }
