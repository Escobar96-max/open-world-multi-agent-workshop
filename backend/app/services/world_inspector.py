"""
World Inspector Service:
Dynamically compiles real-time telemetry from the Autonomous 2D Spatial Engine,
Frequency Lounge audio harmonics, individual agent memory vaults, and governance files.
Provides rich, grounded context to Orion Prime and Nova in Unified C2 Desk.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("c2.world_inspector")


class WorldInspector:
    def __init__(self, vault_path: Optional[Path] = None):
        self.vault = Path(vault_path) if vault_path else settings.vault_path

    def get_live_world_telemetry(self) -> Dict[str, Any]:
        """
        Reads live spatial positions, frequency state, lounge chatter,
        individual agent memories, and governance state across the world.
        """
        telemetry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "spatial_agents": {},
            "frequency_state": {},
            "state_summary": "",
            "recent_lounge_talks": "",
            "agent_activities": {},
            "governance_summary": ""
        }

        # 1. Live Spatial Grid State
        try:
            from app.routers.spatial_router import get_spatial_engine, get_dj_node
            engine = get_spatial_engine()
            dj = get_dj_node()

            spatial_dict = {}
            for aid, a in engine.agents.items():
                spatial_dict[aid] = {
                    "name": a.name,
                    "role": a.role,
                    "x": round(a.x, 1),
                    "y": round(a.y, 1),
                    "zone": a.zone,
                    "temperature": a.temperature,
                    "status": a.status
                }
            telemetry["spatial_agents"] = spatial_dict
            telemetry["simulation_tick"] = engine.tick_count
            telemetry["frequency_state"] = dj.get_state()
        except Exception as e:
            logger.debug(f"Live spatial engine inspect warning: {e}")

        # 2. World/state.md (Persisted World State)
        state_file = self.vault / "World" / "state.md"
        if state_file.exists():
            try:
                telemetry["state_summary"] = state_file.read_text(encoding="utf-8").strip()
            except Exception as e:
                telemetry["state_summary"] = f"Error reading state.md: {e}"
        else:
            telemetry["state_summary"] = "Grid initialized: Work Plaza (0-50), Lounge (51-100), Active Frequency: 432Hz."

        # 3. Frequency Lounge Logs (vault/World/lounge_logs.md)
        lounge_file = self.vault / "World" / "lounge_logs.md"
        if lounge_file.exists():
            try:
                lines = [l.strip() for l in lounge_file.read_text(encoding="utf-8").splitlines() if l.strip().startswith("- `")]
                if lines:
                    telemetry["recent_lounge_talks"] = "\n".join(lines[-6:])
                else:
                    telemetry["recent_lounge_talks"] = "No recent dialogue in Frequency Lounge."
            except Exception as e:
                telemetry["recent_lounge_talks"] = f"Lounge logs read error: {e}"
        else:
            telemetry["recent_lounge_talks"] = "No recent conversations in Frequency Lounge."

        # 4. Individual Agent Recent Activities & Memories (vault/Agents/*/memories/*.md)
        agent_activities: Dict[str, Dict[str, Any]] = {}
        agents_dir = self.vault / "Agents"
        if agents_dir.exists():
            for agent_folder in sorted(agents_dir.iterdir()):
                if agent_folder.is_dir():
                    agent_name = agent_folder.name
                    mem_dir = agent_folder / "memories"
                    if mem_dir.exists():
                        md_files = sorted(mem_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
                        if md_files:
                            latest_file = md_files[0]
                            try:
                                text = latest_file.read_text(encoding="utf-8")
                                # Extract header or key observation
                                summary = ""
                                lines = text.splitlines()
                                title = latest_file.stem
                                for idx, line in enumerate(lines):
                                    if line.startswith("title:"):
                                        title = line.replace("title:", "").strip().strip("'\"")
                                    elif line.startswith("## ") or line.startswith("### "):
                                        heading_text = line.strip("# ")
                                        # Look for subsequent body text
                                        body_lines = [
                                            l.strip() for l in lines[idx + 1:idx + 6]
                                            if l.strip() and not l.startswith("#") and not l.startswith("---")
                                        ]
                                        summary = f"{heading_text}: {body_lines[0]}" if body_lines else heading_text
                                        break
                                if not summary:
                                    summary = text[:250].strip()

                                agent_activities[agent_name] = {
                                    "latest_memory_file": latest_file.name,
                                    "title": title,
                                    "snippet": summary[:200]
                                }
                            except Exception as ex:
                                logger.debug(f"Failed to read memory for {agent_name}: {ex}")

        telemetry["agent_activities"] = agent_activities

        # 5. Governance & Bounties
        gov_parts = []
        prop_file = self.vault / "World" / "proposals.md"
        if prop_file.exists():
            try:
                p_text = prop_file.read_text(encoding="utf-8")[:400].strip()
                if p_text:
                    gov_parts.append(f"Proposals:\n{p_text}")
            except Exception:
                pass
        bounty_file = self.vault / "World" / "bounty_board.md"
        if bounty_file.exists():
            try:
                b_text = bounty_file.read_text(encoding="utf-8")[:400].strip()
                if b_text:
                    gov_parts.append(f"Bounty Board:\n{b_text}")
            except Exception:
                pass
        telemetry["governance_summary"] = "\n\n".join(gov_parts) if gov_parts else "All governance parameters nominal."

        return telemetry

    def format_telemetry_prompt_block(self, telemetry: Optional[Dict[str, Any]] = None) -> str:
        """Formats telemetry into an LLM-ready context block."""
        data = telemetry or self.get_live_world_telemetry()

        # Format spatial agent coordinates list
        spatial_lines = []
        for aid, a in data.get("spatial_agents", {}).items():
            spatial_lines.append(f"  - @{aid} ({a['name']}): Coordinates ({a['x']}, {a['y']}) in {a['zone']} [Temp: {a['temperature']}, Status: {a['status']}]")
        spatial_summary = "\n".join(spatial_lines) if spatial_lines else "  - Spatial simulation agents offline or loading."

        freq_state = data.get("frequency_state", {})
        freq_str = f"{freq_state.get('frequency', 432)}Hz ({freq_state.get('mode', 'ambient')})"

        return f"""=== LIVE AGENT WORLD TELEMETRY (REAL TIME) ===
[Ambient Audio Frequency]: {freq_str}
[Simulation Tick]: {data.get('simulation_tick', 0)}

[Spatial Agents & Coordinates]:
{spatial_summary}

[Lounge Discussions & Atmosphere]:
{data.get('recent_lounge_talks', 'No recent dialogue.')}

[Individual Agent Activities & Memories]:
{json.dumps(data.get('agent_activities', {}), indent=2)}

[Governance & Proposals]:
{data.get('governance_summary', 'All parameters nominal.')}
=============================================="""


# Global World Inspector instance
world_inspector = WorldInspector()


def get_world_inspector() -> WorldInspector:
    return world_inspector
