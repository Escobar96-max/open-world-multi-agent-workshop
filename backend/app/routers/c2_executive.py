"""
C2 Executive Router:
Exposes REST endpoints for the Orion Prime & Nova Dual-Executive Desk,
Task Kanban boards, and Group Chat Hubs.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.executive_duo import ExecutiveDuo

router = APIRouter(prefix="/api/v1/c2", tags=["C2 Executive"])

# Global singleton instance of ExecutiveDuo
_executive_duo = ExecutiveDuo()


def get_executive_duo() -> ExecutiveDuo:
    return _executive_duo


class DuoChatRequest(BaseModel):
    prompt: str
    operator: Optional[str] = "Operator"


class TaskActionRequest(BaseModel):
    task_id: str
    summary: Optional[str] = "Approved and verified."


class GroupChatRequest(BaseModel):
    group_id: str
    sender: str
    text: str


@router.post("/duo-chat")
async def duo_chat_endpoint(req: DuoChatRequest):
    """
    Submits Operator natural language prompt to Orion & Nova.
    Orion plans the Task DAG, Nova validates and syncs Obsidian memory.
    """
    duo = get_executive_duo()
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty.")

    result = await duo.process_directive(req.prompt.strip(), operator=req.operator or "Operator")
    return result


@router.get("/tasks")
def get_tasks_endpoint():
    """Returns categorized Kanban tasks for real-time board rendering."""
    duo = get_executive_duo()
    return duo.get_tasks()


@router.post("/tasks/approve")
def approve_task_endpoint(req: TaskActionRequest):
    """Approves a task in 'needs_approval' status."""
    duo = get_executive_duo()
    res = duo.approve_task(req.task_id)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error"))
    return res


@router.post("/tasks/complete")
def complete_task_endpoint(req: TaskActionRequest):
    """Marks a task as completed."""
    duo = get_executive_duo()
    res = duo.complete_task(req.task_id, summary=req.summary or "Completed.")
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("error"))
    return res


@router.get("/groups")
def get_groups_endpoint():
    """Lists available sub-team channels."""
    return {
        "groups": [
            {"id": "executive_suite", "name": "👑 Executive Suite", "lead": "Orion Prime & Nova"},
            {"id": "marketing_squad", "name": "📈 Marketing Squad", "lead": "Growth Operative"},
            {"id": "defense_guard", "name": "🛡️ Defense Guard", "lead": "Sentinel Alpha"},
            {"id": "chill_lounge", "name": "🎵 432Hz Chill Lounge", "lead": "DJ Frequency"}
        ]
    }


@router.get("/group-chat")
def get_group_chat_endpoint(group_id: str = "executive_suite"):
    """Fetches chat stream for a specific group."""
    duo = get_executive_duo()
    return {
        "group_id": group_id,
        "messages": duo.get_group_messages(group_id)
    }


@router.post("/group-chat")
def post_group_chat_endpoint(req: GroupChatRequest):
    """Posts a message to a sub-team channel."""
    duo = get_executive_duo()
    res = duo.post_group_message(req.group_id, req.sender, req.text)
    return res
