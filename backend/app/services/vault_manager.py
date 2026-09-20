"""
Obsidian Vault Manager:
Thread-safe Markdown CRUD operations with strict regex validation,
YAML frontmatter parsing, and bidirectional [[wikilink]] generation.
"""

import os
import re
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import frontmatter

from app.config import settings

AGENT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


class VaultSecurityError(Exception):
    """Raised when an invalid or insecure agent_id is provided."""
    pass


class VaultManager:
    """Thread-safe manager for reading and writing to the Obsidian knowledge vault."""

    _lock = threading.Lock()

    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = Path(vault_path or settings.vault_path)
        self.agents_dir = self.vault_path / "Agents"
        self.world_dir = self.vault_path / "World"

        # Ensure base directories exist
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.world_dir.mkdir(parents=True, exist_ok=True)

    def validate_agent_id(self, agent_id: str) -> str:
        """Validates agent ID against strict security regex."""
        clean_id = agent_id.strip()
        if not AGENT_ID_REGEX.match(clean_id):
            raise VaultSecurityError(
                f"Invalid agent_id '{agent_id}'. Must be 3-32 alphanumeric characters or underscores."
            )
        return clean_id

    def append_memory(
        self,
        agent_id: str,
        observation: str,
        importance: int = 5,
        tags: Optional[List[str]] = None,
        source_url: str = "",
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Creates and appends an Obsidian-compatible markdown note with YAML frontmatter.
        Destination: vault/Agents/{agent_id}/memories/{timestamp}_{slug}.md
        """
        valid_id = self.validate_agent_id(agent_id)
        now = datetime.now(timezone.utc)
        timestamp_slug = now.strftime("%Y%m%d_%H%M%S")
        iso_str = now.isoformat()

        agent_memories_dir = self.agents_dir / valid_id / "memories"
        with self._lock:
            agent_memories_dir.mkdir(parents=True, exist_ok=True)

        clean_title = title or f"Memory {timestamp_slug}"
        slug = re.sub(r"[^\w\s-]", "", clean_title).strip().lower()
        slug = re.sub(r"[-\s]+", "_", slug)[:40] or "observation"

        unique_suffix = uuid.uuid4().hex[:6]
        filename = f"{timestamp_slug}_{slug}_{unique_suffix}.md"
        file_path = agent_memories_dir / filename

        default_tags = ["agent-world", "memory", f"agent-{valid_id.lower()}"]
        merged_tags = list(dict.fromkeys(default_tags + (tags or [])))

        post = frontmatter.Post(
            content=f"""# [[{valid_id}]] Observation: {clean_title}

- **Agent**: [[{valid_id}]]
- **Importance**: `{importance}/10`
- **Source URL**: [{source_url}]({source_url})
- **Timestamp**: `{now.strftime('%Y-%m-%d %H:%M:%S UTC')}`

---

## 📝 Observation Content
{observation}

---
*Synced to [[{valid_id}]] Obsidian Knowledge Vault.*
""",
            title=clean_title,
            agent=f"[[{valid_id}]]",
            timestamp=iso_str,
            importance=importance,
            source_url=source_url,
            tags=merged_tags,
            **(metadata or {})
        )

        with self._lock:
            file_path.write_text(frontmatter.dumps(post), encoding="utf-8")

        return file_path

    def recall_memories(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Recalls the latest memories for an agent."""
        valid_id = self.validate_agent_id(agent_id)
        agent_memories_dir = self.agents_dir / valid_id / "memories"

        if not agent_memories_dir.exists():
            return []

        with self._lock:
            files = sorted(agent_memories_dir.glob("*.md"), reverse=True)[:limit]
            results = []
            for f in files:
                try:
                    post = frontmatter.loads(f.read_text(encoding="utf-8"))
                    results.append({
                        "filename": f.name,
                        "path": str(f),
                        "metadata": post.metadata,
                        "content": post.content
                    })
                except Exception:
                    continue
            return results

    def append_lounge_log(self, speaker: str, message: str) -> None:
        """Appends dialogue to the Frequency Lounge stream."""
        lounge_file = self.world_dir / "lounge_logs.md"
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        entry = f"\n- `[{now_str}]` **{speaker}**: {message}\n"

        with self._lock:
            if not lounge_file.exists():
                lounge_file.write_text("# Frequency Lounge Dialogue Stream\n", encoding="utf-8")
            with open(lounge_file, "a", encoding="utf-8") as fh:
                fh.write(entry)

    def read_state(self) -> Dict[str, Any]:
        """Reads global world state from World/state.md."""
        state_file = self.world_dir / "state.md"
        with self._lock:
            if not state_file.exists():
                return {"status": "offline"}
            try:
                post = frontmatter.loads(state_file.read_text(encoding="utf-8"))
                return {"metadata": post.metadata, "content": post.content}
            except Exception:
                return {"status": "error"}
