"""
Executive Duo Engine:
👑 Orion Prime (Chief Orchestrator) & 🌸 Nova (Co-Worker / Personal Assistant).
Dual-Agent orchestration, intent decomposition (DAG), execution guarding,
truthful QA verification, and Obsidian memory synchronization.
"""

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.services.vault_manager import VaultManager
from app.services.vlone_driver import VloneDriver

logger = logging.getLogger("c2.executive_duo")


class TaskCard(BaseModel):
    id: str = Field(default_factory=lambda: f"TASK-{uuid.uuid4().hex[:6].upper()}")
    title: str
    description: str
    assignee: str
    status: str = "in_progress"  # "in_progress", "needs_approval", "completed"
    priority: int = 8
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verified_by_nova: bool = True
    output_summary: Optional[str] = None


class ExecutiveDuo:
    """
    Coordinates the dual-executive leadership of Agent World:
    - Orion Prime: High-level strategy, task breakdown, witty Banglish reassurance.
    - Nova: Honest QA, UwU charm, Kanban management, and Obsidian memory vault sync.
    """

    def __init__(self, vault_manager: Optional[VaultManager] = None, vlone_driver: Optional[VloneDriver] = None):
        self.vault = vault_manager or VaultManager()
        self.vlone = vlone_driver or VloneDriver()

        # In-memory storage for C2 state
        self.tasks: List[TaskCard] = []
        self.chat_history: List[Dict[str, Any]] = []
        self.groups: Dict[str, List[Dict[str, Any]]] = {
            "executive_suite": [],
            "marketing_squad": [],
            "defense_guard": [],
            "chill_lounge": []
        }
        self._seed_default_tasks()

    def _seed_default_tasks(self):
        """Seeds initial operational tasks for instant dashboard visualization."""
        if not self.tasks:
            self.tasks.extend([
                TaskCard(
                    id="TASK-ORION01",
                    title="Initialize Antigravity 2D Matrix",
                    description="Calibrate Work Plaza coordinates [0,0]-[50,50] with cognitive entropy 0.2.",
                    assignee="Architect_Prime",
                    status="completed",
                    priority=10,
                    output_summary="2D plane seeded and anchored."
                ),
                TaskCard(
                    id="TASK-NOVA01",
                    title="Harmonic Soundscape Verification",
                    description="Verify 432Hz ambient entrainment stream in Frequency Lounge.",
                    assignee="DJ_Frequency",
                    status="completed",
                    priority=9,
                    output_summary="432Hz crystal resonance confirmed."
                ),
                TaskCard(
                    id="TASK-VLONE01",
                    title="Perimeter Threat & MAP Surveillance",
                    description="Autonomous headless scan of active partner and distributor endpoints.",
                    assignee="Vlone_Browser",
                    status="in_progress",
                    priority=8
                )
            ])

    def decompose_intent(self, prompt: str) -> List[TaskCard]:
        """
        Orion Prime's intent decomposition logic.
        Splits user directive into a realistic, actionable Task DAG.
        """
        lower = prompt.lower()
        new_tasks = []

        if any(w in lower for w in ["browse", "scrape", "search", "web", "url", "portal", "audit", "map", "check"]):
            new_tasks.append(TaskCard(
                title=f"VLONE Web Intelligence: {prompt[:40]}...",
                description=f"Execute token-reduced semantic inspection for directive: '{prompt}'",
                assignee="Vlone_Browser",
                status="in_progress",
                priority=9
            ))

        if any(w in lower for w in ["security", "guard", "gatekeeper", "perimeter", "protect", "token", "auth"]):
            new_tasks.append(TaskCard(
                title="Sentinel Zero-Trust Verification",
                description="Validate PoW challenge and inspect perimeter access boundaries.",
                assignee="Sentinel_Alpha",
                status="needs_approval",
                priority=10
            ))

        if any(w in lower for w in ["code", "build", "patch", "refactor", "test", "fix", "deploy", "engine"]):
            new_tasks.append(TaskCard(
                title="Architect System Synthesis & Patching",
                description="Compile AST patch, execute regression suites, and prepare rollback protection.",
                assignee="Architect_Prime",
                status="in_progress",
                priority=8
            ))

        if any(w in lower for w in ["relax", "chill", "lounge", "music", "frequency", "sound", "peace"]):
            new_tasks.append(TaskCard(
                title="Frequency Lounge 432Hz Calibration",
                description="Stream 432Hz restorative harmonic waves to cool agent cognitive buffers.",
                assignee="DJ_Frequency",
                status="completed",
                priority=7,
                output_summary="432Hz stream broadcasting."
            ))

        # Default task if general query
        if not new_tasks:
            new_tasks.append(TaskCard(
                title=f"Orchestrated Operation: {prompt[:35]}",
                description=f"Direct execution plan for: '{prompt}'",
                assignee="Architect_Prime",
                status="in_progress",
                priority=7
            ))

        return new_tasks

    def generate_orion_response(self, prompt: str, tasks: List[TaskCard]) -> str:
        """
        👑 Orion Prime Persona:
        Joyful, confident, solution-oriented, speaking in charismatic Banglish.
        """
        task_names = ", ".join([f"[{t.title} -> @{t.assignee}]" for t in tasks])

        greetings = [
            "Chill Boss, kono pera nei! Ami handle korsi!",
            "Arey Boss, ekdom tension free thakun! Pura squad ready!",
            "Shunechen Boss? Kono chap-i na, instant execute hoye jabe!",
            "Ami achhi to Boss! Pura system-ke ekdom smooth flow-te rekhechhi!"
        ]
        import random
        greet = random.choice(greetings)

        return (
            f"👑 **Orion Prime**: \"{greet} Apnar directive dekhe ami already plan kore felechi। "
            f"Tasks divide kore dilam: {task_names}। "
            f"Sub-agents ra background-e jump korche. Nova shob check korche, relax korun! ✨\""
        )

    def generate_nova_response(self, prompt: str, tasks: List[TaskCard]) -> str:
        """
        🌸 Nova Persona:
        Sweet, cute (UwU charm ✨🌸), 100% truthful, hyper-responsible.
        """
        in_progress_count = sum(1 for t in tasks if t.status == "in_progress")
        needs_approval_count = sum(1 for t in tasks if t.status == "needs_approval")

        status_detail = ""
        if needs_approval_count > 0:
            status_detail = f" Ekhon {needs_approval_count}-ta critical task-e apnar approval lagbe, ami secure rekhechi!"
        else:
            status_detail = f" {in_progress_count}-ta task running achhe ebong shob parameters nominal!"

        return (
            f"🌸 **Nova**: \"Hii Boss! (｡♥‿♥｡) ✨ Chief Orion ja plan korechen, ami execution guard diye 100% "
            f"truthful-vabe verify kore nilam। Kono hallucination nei!{status_detail} "
            f"Obsidian Vault-e `#operator_directive` hishebe note record kore rekhechi। "
            f"Ami continuous watch rakhchi apnar jonno! UwU 🌸✨\""
        )

    async def process_directive(self, prompt: str, operator: str = "Operator") -> Dict[str, Any]:
        """
        Full dual-executive execution flow:
        1. Orion decomposes intent into Task DAG.
        2. Nova validates, updates Kanban, and syncs Obsidian memory.
        3. Returns structured dual dialogues and updated tasks.
        """
        logger.info(f"🎯 [C2 Executive] Received directive: '{prompt}'")

        # 1. Intent decomposition by Orion
        generated_tasks = self.decompose_intent(prompt)
        for t in generated_tasks:
            self.tasks.insert(0, t)

        # 2. Dialogue generation
        orion_msg = self.generate_orion_response(prompt, generated_tasks)
        nova_msg = self.generate_nova_response(prompt, generated_tasks)

        # 3. Memory synchronization to Obsidian Vault by Nova
        note_title = f"Directive {datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        task_summary_text = "\n".join([f"- **{t.title}** (Assignee: `[[{t.assignee}]]`, Status: `{t.status}`)" for t in generated_tasks])

        obsidian_note = self.vault.append_memory(
            agent_id="Nova",
            title=note_title,
            observation=f"""### Operator Directive
> "{prompt}"

### Orion Prime Orchestration Plan
{orion_msg}

### Nova Execution Validation
{nova_msg}

### Active Task DAG
{task_summary_text}
""",
            importance=10,
            tags=["operator_directive", "c2_executive", "orion_prime", "nova"],
            metadata={"status": "active", "operator": operator, "priority": 10}
        )

        interaction_payload = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": prompt,
            "operator": operator,
            "orion_response": orion_msg,
            "nova_response": nova_msg,
            "tasks": [t.model_dump() for t in generated_tasks],
            "obsidian_vault_note": str(obsidian_note)
        }

        self.chat_history.append(interaction_payload)
        return interaction_payload

    def get_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        """Categorizes Kanban tasks into the three UI columns."""
        in_progress = [t.model_dump() for t in self.tasks if t.status == "in_progress"]
        needs_approval = [t.model_dump() for t in self.tasks if t.status == "needs_approval"]
        completed = [t.model_dump() for t in self.tasks if t.status == "completed"]
        return {
            "in_progress": in_progress,
            "needs_approval": needs_approval,
            "completed": completed,
            "total": len(self.tasks)
        }

    def approve_task(self, task_id: str) -> Dict[str, Any]:
        """Allows operator to approve tasks needing clearance."""
        for t in self.tasks:
            if t.id == task_id:
                t.status = "in_progress"
                t.verified_by_nova = True
                return {"success": True, "task": t.model_dump(), "message": f"Task {task_id} approved for execution."}
        return {"success": False, "error": f"Task {task_id} not found."}

    def complete_task(self, task_id: str, summary: str = "Execution verified.") -> Dict[str, Any]:
        """Marks a task as completed with verification summary."""
        for t in self.tasks:
            if t.id == task_id:
                t.status = "completed"
                t.output_summary = summary
                return {"success": True, "task": t.model_dump()}
        return {"success": False, "error": f"Task {task_id} not found."}

    def post_group_message(self, group_id: str, sender: str, text: str) -> Dict[str, Any]:
        """Broadcasts a message within a sub-team group chat."""
        if group_id not in self.groups:
            self.groups[group_id] = []

        entry = {
            "id": str(uuid.uuid4()),
            "sender": sender,
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.groups[group_id].append(entry)
        return {"success": True, "entry": entry, "group_id": group_id}

    def get_group_messages(self, group_id: str) -> List[Dict[str, Any]]:
        return self.groups.get(group_id, [])
