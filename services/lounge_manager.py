import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from services.vault_manager import VaultManager

logger = logging.getLogger("LoungeManager")

class LoungeManager:
    """
    Manages autonomous agent social interactions and after-hours dialogue in The Frequency Lounge:
    - Appends structured conversations to /vault/World/lounge_logs.md
    - Enriches logs with active DJ frequency, agent cognitive temperature, and timestamp
    - Exposes API for recent conversation history retrieval
    """
    def __init__(self, vault_manager: Optional[VaultManager] = None):
        self.vault = vault_manager or VaultManager()
        self.log_file = self.vault.vault_root / "World" / "lounge_logs.md"
        self._ensure_log_file_initialized()

    def _ensure_log_file_initialized(self):
        """Creates lounge_logs.md with proper table header if not existing."""
        if not self.log_file.exists():
            header = """---
title: "The Frequency Lounge: After-Hours Dialogue Stream"
description: "Generative conversations, philosophical banter, and social bonds between autonomous agents"
status: "ACTIVE"
---

# 🍸 The Frequency Lounge: Dialogue Logs

| Timestamp | Frequency | Speaker | Listener / Target | Temperature | Dialogue Excerpt |
| :--- | :--- | :--- | :--- | :---: | :--- |
"""
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            self.log_file.write_text(header, encoding="utf-8")
            logger.info("Initialized /vault/World/lounge_logs.md")

    def record_dialogue(
        self,
        speaker_id: str,
        message: str,
        frequency_hz: int,
        listener_id: Optional[str] = None,
        temperature: float = 1.6
    ) -> Dict[str, Any]:
        """Appends a new conversation entry to lounge_logs.md."""
        self.vault.validate_identifier(speaker_id)
        if listener_id:
            self.vault.validate_identifier(listener_id)

        clean_message = message.strip().replace("\n", " ").replace("|", "\\|")
        now_iso = datetime.now(timezone.utc).isoformat()
        listener_display = f"[[{listener_id}]]" if listener_id else "All Nodes"

        row = f"| {now_iso} | {frequency_hz}Hz | [[{speaker_id}]] | {listener_display} | {temperature:.1f} | \"{clean_message}\" |\n"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(row)

        logger.info(f"🍸 Lounge dialogue recorded from [[{speaker_id}]]: {clean_message[:40]}...")
        return {
            "timestamp": now_iso,
            "speaker": speaker_id,
            "listener": listener_id or "All",
            "frequency_hz": frequency_hz,
            "temperature": temperature,
            "message": clean_message
        }

    def get_recent_logs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Parses the most recent dialogue entries from lounge_logs.md."""
        if not self.log_file.exists():
            return []

        lines = self.log_file.read_text(encoding="utf-8").splitlines()
        log_rows = []
        for line in reversed(lines):
            line_str = line.strip()
            if line_str.startswith("|") and not line_str.startswith("| Timestamp") and not line_str.startswith("| :---"):
                parts = [p.strip() for p in line_str.split("|")[1:-1]]
                if len(parts) >= 6:
                    log_rows.append({
                        "timestamp": parts[0],
                        "frequency": parts[1],
                        "speaker": parts[2],
                        "listener": parts[3],
                        "temperature": parts[4],
                        "message": parts[5].strip('"')
                    })
                if len(log_rows) >= limit:
                    break
        return log_rows
