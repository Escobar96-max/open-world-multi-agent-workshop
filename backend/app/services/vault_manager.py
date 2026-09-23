"""
Obsidian Vault Manager:
Thread-safe Markdown CRUD operations with strict regex validation,
YAML frontmatter parsing, and bidirectional [[wikilink]] generation.
"""

import os
import re
import uuid
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import frontmatter

from app.config import settings

AGENT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,32}$")


class VaultSecurityError(Exception):
    """Raised when an invalid or insecure agent_id is provided."""
    pass


class EpistemicTruthError(Exception):
    """Raised when knowledge fails Nova's Laya Epistemic Truth Gate (confidence < 0.90)."""
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

    def append_episodic_event(
        self,
        agent_id: str,
        observation: str,
        importance_score: int = 7,
        target_entity: str = "RLCD_Judge",
        location: str = "Cognitive_Sanctum",
        zone: str = "Frequency_Lounge",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Records an episodic distillation or cognitive evaluation event to the Obsidian Vault.
        Destination: vault/Agents/{agent_id}/memories/{timestamp}_episodic_{slug}.md
        Also logs reflection to the Frequency Lounge stream.
        """
        valid_id = self.validate_agent_id(agent_id)
        now = datetime.now(timezone.utc)
        timestamp_slug = now.strftime("%Y%m%d_%H%M%S")
        title = f"Episodic Distillation {timestamp_slug}"

        extra_meta = {
            "type": "episodic_event",
            "target_entity": target_entity,
            "location": location,
            "zone": zone,
            "importance_score": importance_score,
            **(metadata or {})
        }
        tags = ["episodic", "rlcd", "distillation", f"agent-{valid_id.lower()}", f"zone-{zone.lower().replace(' ', '_')}"]

        path = self.append_memory(
            agent_id=valid_id,
            observation=observation,
            importance=importance_score,
            tags=tags,
            title=title,
            metadata=extra_meta
        )

        try:
            self.append_lounge_log(
                speaker=target_entity,
                message=f"[{location} | {zone}] Distilled trace for [[{valid_id}]]: {observation[:120]}"
            )
        except Exception:
            pass

        return path

    def verify_epistemic_truth(
        self,
        source_context: str,
        statement: str,
        threshold: float = 0.90
    ) -> Dict[str, Any]:
        """
        Nova PA's Laya Truth Gate:
        Evaluates calibrated confidence P(true) before committing knowledge to vault.
        Threshold: 0.90 (90% calibrated confidence).
        """
        from app.services.laya_decision_engine import get_laya_engine
        laya = get_laya_engine()
        confidence = laya.ask_noul(source_context, statement)
        verified = confidence >= threshold
        return {
            "verified": verified,
            "confidence": confidence,
            "threshold": threshold,
            "statement": statement
        }

    def append_verified_memory(
        self,
        agent_id: str,
        observation: str,
        source_context: str,
        importance_score: int = 8,
        tags: Optional[List[str]] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        threshold: float = 0.90
    ) -> Path:
        """
        Appends memory only after passing Nova's Laya Epistemic Truth Gate.
        Rejects unverified or hallucinated claims with EpistemicTruthError.
        """
        verification = self.verify_epistemic_truth(
            source_context=source_context,
            statement=observation,
            threshold=threshold
        )
        if not verification["verified"]:
            raise EpistemicTruthError(
                f"Nova Truth Gate Rejected: Confidence {verification['confidence']:.2f} is below threshold {threshold:.2f}."
            )

        memory_tags = list(tags or [])
        if "verified_truth" not in memory_tags:
            memory_tags.append("verified_truth")

        extra_meta = {
            **(metadata or {}),
            "epistemic_confidence": verification["confidence"],
            "verified_by": "Nova_Truth_Gate",
            "verification_engine": "Laya_Noul"
        }

        return self.append_memory(
            agent_id=agent_id,
            observation=observation,
            importance=importance_score,
            tags=memory_tags,
            title=title,
            metadata=extra_meta
        )

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

    def append_lounge_log(self, speaker: str = "", message: str = "", sender: Optional[str] = None) -> None:
        """Appends dialogue to the Frequency Lounge stream."""
        effective_speaker = speaker or sender or "System"
        lounge_file = self.world_dir / "lounge_logs.md"
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        # Sanitize sensitive patterns (passwords, credentials, auth tokens)
        sanitized_msg = re.sub(r"(?i)(pass(?:word)?\s*[:=]\s*)[^\s,]+", r"\1[REDACTED]", message)
        sanitized_msg = re.sub(r"(?i)(pass\s+)\d{4,}", r"\1[REDACTED]", sanitized_msg)

        entry = f"\n- `[{now_str}]` **{effective_speaker}**: {sanitized_msg}\n"

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

    def recall_multi_day_memories(self, days: int = 7) -> Dict[str, List[Dict[str, Any]]]:
        """
        Gathers memory files across all agents in the vault,
        grouped by calendar date (YYYY-MM-DD), within the last `days`.
        """
        by_date: Dict[str, List[Dict[str, Any]]] = {}
        if not self.agents_dir.exists():
            return by_date

        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).date()
        cutoff_prefix = cutoff_date.strftime("%Y%m%d")

        with self._lock:
            # Look across all agent memory directories
            all_files = list(self.agents_dir.glob("*/memories/*.md"))

        # Pre-filter candidates by eight-digit YYYYMMDD prefix
        candidate_files = []
        for f in all_files:
            prefix8 = f.name[:8]
            if prefix8.isdigit() and len(prefix8) == 8 and prefix8 < cutoff_prefix:
                continue
            candidate_files.append(f)

        for f in sorted(candidate_files, reverse=True):
            try:
                post = frontmatter.loads(f.read_text(encoding="utf-8"))
                meta = post.metadata or {}
                # Date extraction: frontmatter timestamp or filename prefix
                ts = meta.get("timestamp", f.name[:8])
                date_str = ts[:10] if isinstance(ts, str) and len(ts) >= 10 else f.name[:8]
                if len(date_str) == 8 and date_str.isdigit():
                    date_str = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

                # Filter out entries older than requested calendar days range
                try:
                    entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    if entry_date < cutoff_date:
                        continue
                except ValueError:
                    pass

                content = post.content or ""
                directive_m = re.search(r'### Operator Directive\n>\s*"([^"]+)"', content)
                if not directive_m:
                    directive_m = re.search(r'### Operator [^\n]+\n>\s*"([^"]+)"', content)

                directive = None
                if directive_m:
                    directive = directive_m.group(1).strip()
                elif meta.get("type") == "directive" and meta.get("directive"):
                    directive = str(meta.get("directive")).strip()

                tasks = []
                for tm in re.finditer(r'-\s*\*\*(.*?)\*\*\s*\(Assignee:\s*`\[\[(.*?)\]\]`,\s*Status:\s*`(.*?)`\)', content):
                    tasks.append({
                        "title": tm.group(1).strip(),
                        "assignee": tm.group(2).strip(),
                        "status": tm.group(3).strip()
                    })

                entry = {
                    "filename": f.name,
                    "date": date_str,
                    "title": meta.get("title", f.name),
                    "directive": directive,
                    "tasks": tasks,
                    "agent": meta.get("agent", "[[Nova]]"),
                    "engine": meta.get("engine", "system")
                }
                if date_str not in by_date:
                    by_date[date_str] = []
                by_date[date_str].append(entry)
            except Exception:
                continue

        return by_date

    def get_multi_day_activity_summary(self, days: int = 7) -> str:
        """
        Produces a rich, human-readable multi-day activity report from Obsidian memories,
        summarizing daily operator directives, dispatched sub-agent tasks, and lounge events.
        """
        by_date = self.recall_multi_day_memories(days=days)
        if not by_date:
            return ""

        summary_lines = ["### Multi-Day Historical Activity (Obsidian Vault):"]
        sorted_dates = sorted(by_date.keys(), reverse=True)[:days]

        for d in sorted_dates:
            entries = by_date[d]
            directives = []
            agent_tasks: Dict[str, List[str]] = {}
            for e in entries:
                if e["directive"] and e["directive"] not in directives:
                    directives.append(e["directive"])
                for t in e["tasks"]:
                    assignee = t["assignee"]
                    task_desc = f"{t['title']} ({t['status']})"
                    if assignee not in agent_tasks:
                        agent_tasks[assignee] = []
                    if task_desc not in agent_tasks[assignee]:
                        agent_tasks[assignee].append(task_desc)

            summary_lines.append(f"\n- **Date: {d}** ({len(entries)} logged interactions):")
            if directives:
                recent_dirs = '", "'.join(directives[:3])
                summary_lines.append(f"  - Directives: \"{recent_dirs}\"")
            if agent_tasks:
                summary_lines.append("  - Sub-Agents Engaged:")
                for agent, tasks in sorted(agent_tasks.items()):
                    summary_lines.append(f"    - `@{agent}`: {', '.join(tasks[:2])}")
            else:
                summary_lines.append("  - Routine status inquiries and synchronizations.")

        # Also append lounge logs if any exist
        lounge_file = self.world_dir / "lounge_logs.md"
        if lounge_file.exists():
            try:
                lounge_lines = [l.strip() for l in lounge_file.read_text(encoding="utf-8").splitlines() if l.strip().startswith("- `")]
                if lounge_lines:
                    summary_lines.append("\n- **Recent Frequency Lounge Logs**:")
                    for ll in lounge_lines[-3:]:
                        summary_lines.append(f"  {ll}")
            except Exception:
                pass

        return "\n".join(summary_lines)

