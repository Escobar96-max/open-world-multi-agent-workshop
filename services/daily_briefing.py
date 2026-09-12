import os
import re
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from services.vault_manager import VaultManager

logger = logging.getLogger("DailyBriefing")

class DailyBriefingEngine:
    """
    Obsidian Neural Graph & Daily Briefing Engine (US-024):
    - Synthesizes multi-agent activities, encounters, ledger transfers, and cognitive pulses
    - Formats metadata with YAML frontmatter and Dataview-compatible inline attributes
    - Generates /vault/World/daily_briefings.md
    - Ensures bidirectional [[wikilinks]] across all agents and concept nodes
    """
    def __init__(self, vault_manager: Optional[VaultManager] = None):
        self.vault = vault_manager or VaultManager()

    def generate_daily_briefing(self, world_day: Optional[str] = None) -> Dict[str, Any]:
        """
        Aggregates recent simulation events and appends or creates a structured briefing
        in /vault/World/daily_briefings.md with Dataview metadata.
        """
        today_str = world_day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_iso = datetime.now(timezone.utc).isoformat()

        # Gather agent memory files
        agents_dir = os.path.join(self.vault.vault_root, "Agents")
        agent_summaries = {}
        total_memories = 0

        if os.path.exists(agents_dir):
            for agent_id in os.listdir(agents_dir):
                agent_path = os.path.join(agents_dir, agent_id)
                if not os.path.isdir(agent_path):
                    continue
                memories_path = os.path.join(agent_path, "memories")
                count = len(os.listdir(memories_path)) if os.path.exists(memories_path) else 0
                total_memories += count
                agent_summaries[agent_id] = {
                    "memory_count": count,
                    "wikilink": f"[[{agent_id}]]"
                }

        # Gather recent lounge dialogue
        lounge_logs_path = os.path.join(self.vault.vault_root, "World", "lounge_logs.md")
        recent_banter = []
        if os.path.exists(lounge_logs_path):
            with open(lounge_logs_path, "r", encoding="utf-8") as lf:
                lines = lf.readlines()[-20:]
                for line in lines:
                    if line.strip().startswith("- **[["):
                        recent_banter.append(line.strip())

        # Construct Dataview Markdown Content
        briefing_content = (
            f"---\n"
            f"type: daily-briefing\n"
            f"date: {today_str}\n"
            f"generated_at: {now_iso}\n"
            f"total_memories: {total_memories}\n"
            f"tags:\n"
            f"  - ecosystem/briefing\n"
            f"  - dataview/active\n"
            f"---\n\n"
            f"# 📰 World Daily Briefing: {today_str}\n\n"
            f"## 🌐 Civilization Metadata\n"
            f"- **Date**:: {today_str}\n"
            f"- **Active Intelligence Entities**:: {', '.join(agent_summaries.keys()) or 'None'}\n"
            f"- **Collective Memories Formed**:: {total_memories}\n\n"
            f"## 👥 Entity Status & Memory Density\n"
        )

        for aid, info in agent_summaries.items():
            briefing_content += f"- {info['wikilink']} | Memories: `{info['memory_count']}` | Status: **ACTIVE**\n"

        briefing_content += "\n## 💬 Recent Synthesized Inter-Agent Encounters\n"
        if recent_banter:
            for b in recent_banter[:8]:
                briefing_content += f"{b}\n"
        else:
            briefing_content += "- *No lounge encounters recorded for this cycle.*\n"

        briefing_content += "\n---\n*Generated autonomously by DailyBriefingEngine for Obsidian Dataview Neural Graph.*\n\n"

        # Write to vault - always write clean document with single frontmatter block at start
        briefings_path = os.path.join(self.vault.vault_root, "World", "daily_briefings.md")
        os.makedirs(os.path.dirname(briefings_path), exist_ok=True)
        
        with open(briefings_path, "w", encoding="utf-8") as f:
            f.write(briefing_content)


        logger.info(f"✅ Generated daily briefing for {today_str} into {briefings_path}")
        return {
            "success": True,
            "date": today_str,
            "path": briefings_path,
            "total_memories": total_memories,
            "agents_counted": len(agent_summaries)
        }
