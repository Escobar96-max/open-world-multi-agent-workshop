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
            ("DJ_Frequency", "🎵 DJ Frequency", "Lounge Host", 82.0, 84.0),
            ("Laila", "📈 Laila", "Growth & Market Scout", 28.0, 68.0),
            ("Moly", "🎯 Moly", "Lead Intelligence & OSINT Hunter", 26.0, 70.0),
            ("Dr_Aris", "🔬 Dr. Aris", "Resonance Physics", 35.0, 35.0),
            ("Vector_09", "⚡ Vector-09", "Kinetic Field Recon", 60.0, 40.0),
            ("AEGIS_Core", "🛡️ A.E.G.I.S. Core", "Safety Containment", 10.0, 10.0),
            ("Unit_404", "🤖 Unit-404", "Autonomous Operative", 45.0, 48.0),
            ("Bob", "🛠️ Bob", "Simulation Agent", 52.0, 55.0),
            ("Alice", "💡 Alice", "Simulation Agent", 30.0, 22.0),
            ("Charlie", "🔭 Charlie", "Simulation Agent", 68.0, 70.0)
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

    def generate_encounter_dialogue(self, a1: SpatialAgent, a2: SpatialAgent, intent: str) -> str:
        """Generates contextual dialogue snippet between two encountering agents."""
        pair = {a1.id, a2.id}
        if "Orion_Prime" in pair and "Architect_Prime" in pair:
            return "Orion Prime reviews AST compiler performance and coordinate calibration with Architect Prime in Work Plaza."
        elif "Nova" in pair and "DJ_Frequency" in pair:
            return "Nova synchronizes 432Hz ambient entrainment harmonics with DJ Frequency for optimal lounge focus."
        elif "Orion_Prime" in pair and "Sentinel_Alpha" in pair:
            return "Orion Prime and Sentinel Alpha audit zero-trust perimeter telemetry and access challenges."
        elif "Nova" in pair and "Laila" in pair:
            return "Nova and Laila align on market intelligence telemetry, partner outreach, and MAP compliance proposals."
        elif "Laila" in pair and "Moly" in pair:
            return "Laila dispatches ICP criteria to Moly for deep 4-tier OSINT lead harvesting and ReacherHQ validation."
        elif "Architect_Prime" in pair and "Curator_Node" in pair:
            return "Architect Prime commits verified code AST build notes to Curator Node for Obsidian Vault indexing."
        elif "Orion_Prime" in pair and "Nova" in pair:
            return "Orion Prime and Nova hold an executive sync on active Kanban task throughput and world balance."
        elif "DJ_Frequency" in pair:
            return f"{a1.name} and {a2.name} converse in Frequency Lounge under harmonic audio resonance ({intent})."
        else:
            return f"{a1.name} and {a2.name} synchronized operational state in {a1.zone} ({intent})."

    def check_proximity(self) -> List[Dict[str, Any]]:
        """Calculates pairwise Euclidean distance and logs meaningful encounters <= threshold."""
        import time
        encounters = []
        agent_list = list(self.agents.values())
        now = time.time()

        for i in range(len(agent_list)):
            for j in range(i + 1, len(agent_list)):
                a1 = agent_list[i]
                a2 = agent_list[j]

                dist = math.sqrt((a1.x - a2.x) ** 2 + (a1.y - a2.y) ** 2)
                if dist <= self.proximity_threshold:
                    interaction_intent = "CASUAL_CHAT"
                    try:
                        from app.services.laya_decision_engine import get_laya_engine
                        laya = get_laya_engine()
                        choice, _ = laya.ask_choice(
                            state_text=f"Agent {a1.id} meets {a2.id} in zone {a1.zone}",
                            question="Classify interaction into DEEP_COLLAB, CASUAL_CHAT, or IGNORE",
                            options=["DEEP_COLLAB", "CASUAL_CHAT", "IGNORE"]
                        )
                        interaction_intent = choice
                    except Exception:
                        pass

                    encounter_data = {
                        "agent_1": a1.id,
                        "agent_2": a2.id,
                        "distance": round(dist, 2),
                        "zone": a1.zone,
                        "laya_intent": interaction_intent
                    }
                    encounters.append(encounter_data)

                    # Debounced lounge log dialogue for meaningful interactions (30s cooldown)
                    pair_key = f"{min(a1.id, a2.id)}__{max(a1.id, a2.id)}"
                    last_time = self._recent_encounters.get(pair_key, 0.0)
                    if (now - last_time) > 30.0 and interaction_intent in ["DEEP_COLLAB", "CASUAL_CHAT"]:
                        self._recent_encounters[pair_key] = now
                        dialogue = self.generate_encounter_dialogue(a1, a2, interaction_intent)
                        try:
                            self.vault.append_lounge_log(
                                speaker=f"Spatial_Encounter [{a1.id} & {a2.id}]",
                                message=f"[{interaction_intent}] {dialogue} (Distance: {round(dist, 1)}u)"
                            )
                        except Exception as e:
                            logger.debug(f"Encounter lounge log sync error: {e}")

        return encounters

    def dispatch_agent_to_zone(self, agent_id: str, zone_or_preset: str, task_title: str = "") -> Dict[str, Any]:
        """Dispatches an agent to specific operational coordinates and updates state."""
        if agent_id not in self.agents:
            return {"success": False, "error": f"Agent '{agent_id}' not found."}

        target_coords = {
            "work_plaza": (18.0, 32.0),
            "plaza": (25.0, 25.0),
            "frequency_lounge": (82.0, 84.0),
            "lounge": (75.0, 75.0),
            "market_observatory": (28.0, 68.0),
            "observatory": (28.0, 68.0),
            "gatekeeper": (12.0, 14.0),
            "sanctum": (35.0, 35.0)
        }
        key = zone_or_preset.lower().replace(" ", "_")
        coords = target_coords.get(key, (25.0, 25.0))

        res = self.update_position(agent_id, coords[0], coords[1])
        if res.get("success"):
            agent = self.agents[agent_id]
            if task_title:
                agent.status = f"executing: {task_title[:30]}"
            try:
                self.vault.append_lounge_log(
                    speaker="C2_Executive_Dispatch",
                    message=f"👑 **Executive Dispatch**: [[{agent_id}]] positioned at {agent.zone} [{agent.x}, {agent.y}] for task '{task_title or 'Operational Duty'}'. Nominal status engaged."
                )
            except Exception:
                pass
            self.sync_state_to_vault()
        return res

    def sync_state_to_vault(self) -> None:
        """Writes live spatial grid telemetry, agent positions, and zones to vault/World/state.md."""
        try:
            from datetime import datetime, timezone
            state_file = self.vault.world_dir / "state.md"
            now_iso = datetime.now(timezone.utc).isoformat()

            agent_lines = []
            for a in self.agents.values():
                agent_lines.append(
                    f"- **[[{a.id}]]** ({a.name}): Coordinates `({a.x:.1f}, {a.y:.1f})` | Zone: `{a.zone}` | Temp: `{a.temperature}` | Status: `{a.status}`"
                )
            agents_md = "\n".join(agent_lines)

            content = f"""---
world_name: "Antigravity Spatial World"
status: "online"
ambient_frequency: 432
total_agents: {len(self.agents)}
active_zone: "Work Plaza & Frequency Lounge"
simulation_tick: {self.tick_count}
timestamp: "{now_iso}"
---

# Antigravity Spatial World: Live System State

- **World Grid**: 100x100 Cartesian Matrix (Tick: {self.tick_count})
- **Work Plaza**: (0,0) to (50,50) [Entropy: 0.2 / Deterministic Dev Loop]
- **Frequency Lounge**: (51,51) to (100,100) [Entropy: 1.6 / 432Hz Ambient Resonance]

## 🤖 Active Spatial Agents & Live Coordinates
{agents_md}

## 🌐 Spatial Status Summary
All foundation agents are registered and actively monitored in the 2D spatial plane. Proximity encounters and ambient drift operate synchronously with Unified C2 Executive Desk.
"""
            state_file.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.debug(f"Failed to sync spatial state to vault: {e}")

    def get_latest_agent_speech(self, agent_id: str) -> Optional[str]:
        """Retrieves the most recent speech or dialogue for an agent."""
        import time
        if not hasattr(self, "_agent_recent_speech"):
            self._agent_recent_speech = {}

        entry = self._agent_recent_speech.get(agent_id)
        if entry:
            speech, ts = entry
            # Speech bubble persists for 60 seconds
            if time.time() - ts < 60.0:
                return speech

        # Default contextual thought bubbles based on agent duties
        agent = self.agents.get(agent_id)
        if not agent:
            return None

        defaults = {
            "Bob": "Optimizing AST vector transforms for euclidean math utility...",
            "Alice": "Calibrating quantum variance threshold across Sector 01.",
            "Dr_Aris": "Graviton core precession frequency stabilized at 432Hz.",
            "AEGIS_Core": "Zero-trust firewall active. Outer drifter perimeter secure.",
            "Architect_Prime": "Compiled AST kernel passes zero-regression benchmark.",
            "DJ_Frequency": "Frequency Lounge entrainment locked to 432Hz harmonic wave.",
            "Sentinel_Alpha": "PoW challenge verified. Zero threat vectors detected.",
            "Laila": "Market observatory scan complete. B2B proposals aligned.",
            "Moly": "Hunting verified B2B decision makers via 4-tier OSINT radar and ReacherHQ.",
            "Orion_Prime": "Entire squad nominal. Antigravity grid synchronized.",
            "Nova": "100% verified truth in Obsidian vault! All parameters nominal! UwU ✨",
            "Curator_Node": "Indexing cognitive memories into Obsidian Vault.",
            "Vector_09": "Aerial LiDAR telemetry aligned with 3D city grid.",
            "Unit_404": "Autonomous runtime operating at peak efficiency."
        }
        return defaults.get(agent_id)

    def set_agent_speech(self, agent_id: str, speech: str) -> None:
        """Sets an active speech utterance for an agent."""
        import time
        if not hasattr(self, "_agent_recent_speech"):
            self._agent_recent_speech = {}
        self._agent_recent_speech[agent_id] = (speech, time.time())

    def compile_live_3d_state(self) -> Dict[str, Any]:
        """
        Compiles high-resolution 5D Hyper-Spatial telemetry packet:
        - 3D Coordinates (X, Y, Z) mapped from 2D plane to 3D city space
        - Entity statuses, altitudes, and active speech bubbles
        - Procedural spire infrastructure growth & power load
        - 432Hz Solfeggio harmonics
        """
        from datetime import datetime, timezone
        import time

        entities = []
        for a in self.agents.values():
            # Altitude: ground level is 2.0, recon drones operate at 35-50 AGL
            altitude = 2.0
            if a.id in ["Vector_09", "Valkyrie_Drone_01", "Valkyrie_Drone_02"]:
                altitude = 38.0 + math.sin(self.tick_count * 0.3 + hash(a.id) % 10) * 8.0
            elif a.zone == "Work Plaza":
                altitude = 2.5
            elif a.zone == "Frequency Lounge":
                altitude = 4.0

            # 2D [0, 100] mapped into 3D city coordinate space [-225, 225]
            pos_x = round((a.x - 50.0) * 4.5, 2)
            pos_z = round((a.y - 50.0) * 4.5, 2)
            pos_y = round(altitude, 2)

            entities.append({
                "id": a.id,
                "name": a.name,
                "role": a.role,
                "status": a.status,
                "x": pos_x,
                "y": pos_y,
                "z": pos_z,
                "position": {"x": pos_x, "y": pos_y, "z": pos_z},
                "grid_2d": {"x": a.x, "y": a.y, "zone": a.zone},
                "speech": self.get_latest_agent_speech(a.id),
                "recent_speech": self.get_latest_agent_speech(a.id),
                "temperature": a.temperature
            })

        # Procedural building metrics mapped to 3D Landmark IDs
        spires = {
            "BLD-00": {
                "id": "BLD-00",
                "name": "Quantum Singularity Monolith Spire",
                "title": "Central Command & Graviton Singularity Spire",
                "sector": "Sector 01: Core Plaza",
                "power_load_kw": 1450 + int(math.sin(self.tick_count * 0.2) * 60),
                "coherence_pct": 99.8,
                "phase_lock": "432Hz Locked",
                "height_floors": 42 + min(self.tick_count // 5, 20),
                "occupancy": "Dr. Aris, Vector-09 (Directorate)",
                "status": "ACTIVE_SINGULARITY"
            },
            "BLD-01": {
                "id": "BLD-01",
                "name": "Aegis Defense Citadel",
                "power_load_kw": 980 + int(math.cos(self.tick_count * 0.15) * 40),
                "coherence_pct": 99.4,
                "status": "ARMED_PATROL"
            },
            "BLD-03": {
                "id": "BLD-03",
                "name": "Obsidian Memory Vault Tower",
                "status": "SYNCED_IPFS",
                "coherence_pct": 99.7
            },
            "BLD-04": {
                "id": "BLD-04",
                "name": "Neural Matrix Synthesis Spire",
                "rlvr_status": "ONLINE",
                "ast_nodes_compiled": 128 + self.tick_count * 2,
                "coherence_pct": 98.5
            },
            "quantum_singularity": {
                "name": "Quantum Singularity Monolith Spire",
                "title": "Central Command & Graviton Singularity Spire",
                "sector": "Sector 01: Core Plaza",
                "power_load_kw": 1450 + int(math.sin(self.tick_count * 0.2) * 60),
                "coherence_pct": 99.8,
                "phase_lock": "432Hz Locked",
                "height_floors": 42 + min(self.tick_count // 5, 20),
                "occupancy": "Dr. Aris, Vector-09 (Directorate)"
            },
            "gatekeeper_pow": {
                "name": "Gatekeeper PoW Validator Tower",
                "status": "VALIDATING",
                "hash_difficulty": "0x0000FFFF",
                "active_challenges": 12
            },
            "neural_matrix": {
                "name": "Neural Matrix Synthesis Spire",
                "rlvr_status": "ONLINE",
                "ast_nodes_compiled": 128 + self.tick_count * 2
            },
            "frequency_sanctum": {
                "name": "432Hz Harmonic Frequency Sanctum",
                "frequency_hz": 432.0,
                "ambient_resonance": "NOMINAL_ENTRAINMENT"
            }
        }

        return {
            "type": "LIVE_3D_TELEMETRY",
            "tick": self.tick_count,
            "entities": entities,
            "spires": spires,
            "world_harmonics": 432.04,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def tick(self) -> Dict[str, Any]:
        """Advances simulation state, applies subtle drift, and rotates speech."""
        self.tick_count += 1
        # Apply tiny organic drift within bounds
        for a in self.agents.values():
            if a.zone == "Frequency Lounge":
                # Subtle relaxation wandering
                a.x = self.clamp(a.x + (math.sin(self.tick_count * 0.5) * 0.4))
                a.y = self.clamp(a.y + (math.cos(self.tick_count * 0.5) * 0.4))
            elif a.zone == "Work Plaza":
                # Micro-movement around work stations
                a.x = self.clamp(a.x + (math.cos(self.tick_count * 0.3 + hash(a.id) % 7) * 0.2))
                a.y = self.clamp(a.y + (math.sin(self.tick_count * 0.3 + hash(a.id) % 7) * 0.2))
            zone, temp = self.classify_zone(a.x, a.y)
            a.zone = zone
            a.temperature = temp

        encounters = self.check_proximity()

        # Update speech on encounter
        for enc in encounters:
            a1_id = enc.get("agent_1")
            a2_id = enc.get("agent_2")
            if a1_id and a2_id:
                intent = enc.get("laya_intent", "COLLAB")
                self.set_agent_speech(a1_id, f"Syncing with [[{a2_id}]] ({intent})")
                self.set_agent_speech(a2_id, f"Receiving telemetry from [[{a1_id}]]")

        # Periodically persist live state to vault (every 5 ticks)
        if self.tick_count % 5 == 1:
            self.sync_state_to_vault()

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
