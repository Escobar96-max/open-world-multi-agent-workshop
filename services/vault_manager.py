import os
import re
import yaml
import tempfile
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime, timezone

# Regex for strict agent_id and identifier validation (prevents path traversal)
IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z0-9_]{3,32}$")

class VaultSecurityError(ValueError):
    """Raised when an invalid or malicious path/identifier is provided."""
    pass

class VaultManager:
    def __init__(self, vault_path: Optional[str] = None, vault_root: Optional[str] = None):
        target = vault_root or vault_path
        if target is None:
            target = os.getenv("VAULT_PATH", "./vault")
        self.vault_path = Path(target).resolve()
        self.vault_root = self.vault_path
        self.agents_path = self.vault_path / "Agents"
        self.world_path = self.vault_path / "World"

    def validate_identifier(self, identifier: str) -> str:
        """Validates that an identifier strictly matches ^[a-zA-Z0-9_]{3,32}$."""
        if not identifier or not isinstance(identifier, str):
            raise VaultSecurityError("Identifier must be a non-empty string.")
        
        # Check for path traversal characters
        if ".." in identifier or "/" in identifier or "\\" in identifier:
            raise VaultSecurityError(f"Path traversal characters detected in identifier: {identifier}")

        if not IDENTIFIER_PATTERN.match(identifier):
            raise VaultSecurityError(
                f"Invalid identifier '{identifier}'. Must match ^[a-zA-Z0-9_]{{3,32}}$ (3-32 alphanumeric characters and underscores)."
            )
        return identifier

    def resolve_safe_path(self, base_dir: Path, relative_path: str) -> Path:
        """
        Safely resolves a path relative to base_dir, ensuring it cannot escape base_dir.
        """
        # Strip leading slashes to prevent root escapes
        cleaned_rel = relative_path.lstrip("/\\")
        candidate = (base_dir / cleaned_rel).resolve()
        
        try:
            candidate.relative_to(base_dir.resolve())
        except ValueError:
            raise VaultSecurityError(f"Security Alert: Path traversal attempt blocked: {relative_path}")
            
        return candidate

    def parse_markdown_with_frontmatter(self, raw_text: str) -> Tuple[Dict[str, Any], str]:
        """
        Parses YAML frontmatter enclosed between --- and returns (frontmatter_dict, markdown_body).
        """
        frontmatter = {}
        body = raw_text

        # Pattern for YAML frontmatter at the start of file
        fm_pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
        match = fm_pattern.match(raw_text)
        if match:
            fm_text = match.group(1)
            body = match.group(2)
            try:
                loaded = yaml.safe_load(fm_text)
                if isinstance(loaded, dict):
                    frontmatter = loaded
            except yaml.YAMLError as e:
                frontmatter = {"_yaml_error": str(e)}

        return frontmatter, body

    def format_markdown_with_frontmatter(self, frontmatter: Dict[str, Any], body: str) -> str:
        """
        Serializes frontmatter dict into YAML and combines with markdown body.
        """
        yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False).strip()
        return f"---\n{yaml_str}\n---\n\n{body.strip()}\n"

    def ensure_vault_hierarchy(self) -> None:
        """Initializes physical vault folders if not present."""
        self.agents_path.mkdir(parents=True, exist_ok=True)
        self.world_path.mkdir(parents=True, exist_ok=True)

    def get_agent_dir(self, agent_id: str) -> Path:
        """Returns the safe directory path for an agent."""
        valid_id = self.validate_identifier(agent_id)
        agent_dir = self.resolve_safe_path(self.agents_path, valid_id)
        return agent_dir

    def ensure_agent_structure(self, agent_id: str) -> Path:
        """Ensures that the directory structure for an agent exists."""
        agent_dir = self.get_agent_dir(agent_id)
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "memories").mkdir(exist_ok=True)
        (agent_dir / "relationships").mkdir(exist_ok=True)
        return agent_dir

    def read_file(self, target_path: Path) -> Tuple[Dict[str, Any], str]:
        """Reads file and parses frontmatter."""
        if not target_path.is_file():
            raise FileNotFoundError(f"File does not exist: {target_path}")
        content = target_path.read_text(encoding="utf-8")
        return self.parse_markdown_with_frontmatter(content)

    def write_file(self, target_path: Path, frontmatter: Dict[str, Any], body: str) -> None:
        """Atomically writes formatted markdown with frontmatter."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        formatted = self.format_markdown_with_frontmatter(frontmatter, body)
        fd, temp_name = tempfile.mkstemp(
            dir=str(target_path.parent), prefix=f".{target_path.name}.", suffix=".tmp"
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(formatted)
                f.flush()
                os.fsync(f.fileno())
            temp_path.replace(target_path)
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise

    def get_agent_profile(self, agent_id: str) -> Tuple[Dict[str, Any], str]:
        """Loads the profile.md for an agent."""
        agent_dir = self.get_agent_dir(agent_id)
        profile_file = agent_dir / "profile.md"
        return self.read_file(profile_file)

    def write_agent_profile(self, agent_id: str, frontmatter: Dict[str, Any], body: str) -> None:
        """Writes or updates an agent's profile.md."""
        agent_dir = self.ensure_agent_structure(agent_id)
        profile_file = agent_dir / "profile.md"
        self.write_file(profile_file, frontmatter, body)

    def add_agent_memory(
        self,
        agent_id: str,
        memory_id: str,
        content: str,
        importance: int = 5,
        source: str = "Environment",
        tags: Optional[List[str]] = None
    ) -> Path:
        """
        Writes a memory entry into /vault/Agents/{agent_id}/memories/{memory_id}.md.
        """
        self.validate_identifier(agent_id)
        self.validate_identifier(memory_id)
        
        agent_dir = self.ensure_agent_structure(agent_id)
        memory_file = self.resolve_safe_path(agent_dir / "memories", f"{memory_id}.md")

        now_iso = datetime.now(timezone.utc).isoformat()
        frontmatter = {
            "memory_id": memory_id,
            "agent_id": agent_id,
            "timestamp": now_iso,
            "importance": max(1, min(10, importance)),
            "source": source,
            "tags": tags or []
        }
        
        self.write_file(memory_file, frontmatter, content)
        return memory_file

    def list_agent_memories(self, agent_id: str) -> List[Dict[str, Any]]:
        """Lists all parsed memory files for an agent."""
        self.validate_identifier(agent_id)
        agent_dir = self.ensure_agent_structure(agent_id)
        memories_dir = agent_dir / "memories"
        if not memories_dir.exists():
            return []

        memories = []
        for file_path in memories_dir.glob("*.md"):
            try:
                fm, content = self.read_file(file_path)
                memories.append({
                    "filename": file_path.name,
                    "frontmatter": fm,
                    "content": content,
                    "tags": fm.get("tags", [])
                })
            except Exception:
                continue
        return memories

    def record_relationship(
        self,
        source_agent: str,
        target_agent: str,
        affinity: float,
        notes: str = ""
    ) -> None:
        """
        Creates or updates bidirectional relationship files for both agents.
        """
        self.validate_identifier(source_agent)
        self.validate_identifier(target_agent)

        now_iso = datetime.now(timezone.utc).isoformat()
        
        # 1. Update source -> target
        source_dir = self.ensure_agent_structure(source_agent)
        source_rel_file = source_dir / "relationships" / f"{target_agent}.md"
        fm_source = {
            "source_agent": source_agent,
            "target_agent": target_agent,
            "affinity": max(0.0, min(1.0, affinity)),
            "last_interaction": now_iso
        }
        body_source = f"# Relationship: [[{target_agent}]]\n\n{notes}"
        self.write_file(source_rel_file, fm_source, body_source)

        # 2. Update target -> source (bidirectional)
        target_dir = self.ensure_agent_structure(target_agent)
        target_rel_file = target_dir / "relationships" / f"{source_agent}.md"
        fm_target = {
            "source_agent": target_agent,
            "target_agent": source_agent,
            "affinity": max(0.0, min(1.0, affinity)),
            "last_interaction": now_iso
        }
        body_target = f"# Relationship: [[{source_agent}]]\n\n{notes}"
        self.write_file(target_rel_file, fm_target, body_target)

    def append_world_log(self, log_name: str, log_line: str) -> None:
        """Safely appends a line to a world log file (e.g., admin_logs.md, lounge_logs.md)."""
        clean_name = log_name if log_name.endswith(".md") else f"{log_name}.md"
        target_file = self.resolve_safe_path(self.world_path, clean_name)
        
        target_file.parent.mkdir(parents=True, exist_ok=True)
        if not target_file.exists():
            target_file.write_text(f"# {clean_name}\n\n", encoding="utf-8")

        with open(target_file, "a", encoding="utf-8") as f:
            f.write(f"{log_line.rstrip()}\n")
