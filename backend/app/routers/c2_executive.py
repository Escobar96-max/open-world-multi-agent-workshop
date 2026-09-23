"""
C2 Executive Router:
Exposes REST endpoints for the Orion Prime & Nova Dual-Executive Desk,
Task Kanban boards, and Group Chat Hubs.
"""

import asyncio
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.services.executive_duo import ExecutiveDuo

router = APIRouter(prefix="/api/v1/c2", tags=["C2 Executive"])


class NotificationConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_agent_notification(self, payload: dict):
        for connection in list(self.active_connections):
            try:
                await asyncio.wait_for(connection.send_json(payload), timeout=2.0)
            except Exception:
                if connection in self.active_connections:
                    self.active_connections.remove(connection)


notifier = NotificationConnectionManager()

# Global singleton instance of ExecutiveDuo
_executive_duo = ExecutiveDuo()
_executive_duo.set_notifier(notifier)


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
async def approve_task_endpoint(req: TaskActionRequest):
    """Approves a task in 'needs_approval' status."""
    duo = get_executive_duo()
    res = await duo.approve_task_async(req.task_id)
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


@router.post("/tasks/drain")
async def drain_tasks_endpoint():
    """Manually triggers an immediate autonomous drain cycle on in-progress tasks."""
    duo = get_executive_duo()
    drained = await duo.drain_tasks_step()
    return {"success": True, "drained_count": drained, "tasks": duo.get_tasks()}


@router.get("/groups")
def get_groups_endpoint():
    """Lists available sub-team channels."""
    return {
        "groups": [
            {"id": "executive_suite", "name": "👑 Executive Suite", "lead": "Orion Prime & Nova"},
            {"id": "marketing_squad", "name": "📈 Marketing Squad", "lead": "Laila (Growth & Market Operative)"},
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


class RLCDDistillRequest(BaseModel):
    query: str
    agent_name: Optional[str] = "Nova"


@router.get("/rlcd/status")
def rlcd_status_endpoint():
    """Returns live telemetry for Parallel RLCD engine."""
    duo = get_executive_duo()
    return duo.rlcd_engine.get_status()


@router.post("/rlcd/distill")
async def rlcd_distill_endpoint(req: RLCDDistillRequest):
    """Triggers an explicit RLCD context distillation cycle and logs trace to Obsidian."""
    duo = get_executive_duo()
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    result = await duo.rlcd_engine.run_context_distillation(
        user_query=req.query.strip(),
        agent_name=req.agent_name or "Nova"
    )
    return result


@router.websocket("/ws/notifications")
async def notifications_websocket_endpoint(websocket: WebSocket):
    """
    Real-time push notification bus for proactive agent messages,
    background task completions, and operator sign-off questions.
    """
    await notifier.connect(websocket)
    try:
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to C2 Executive Realtime Notification Bus"
        })
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            if action == "approve_task" and data.get("task_id"):
                duo = get_executive_duo()
                duo.approve_task(data["task_id"])
    except WebSocketDisconnect:
        notifier.disconnect(websocket)
    except Exception:
        notifier.disconnect(websocket)


class ProactiveNotificationRequest(BaseModel):
    sender: Optional[str] = "Orion Prime"
    message: str
    category: Optional[str] = "notification"  # "notification", "question", "urgent"
    options: Optional[List[str]] = None
    task_id: Optional[str] = None
    title: Optional[str] = None


@router.post("/notify")
async def send_proactive_notification_endpoint(req: ProactiveNotificationRequest):
    """Allows agents, background services, or webhooks to push real-time alerts/questions to Operator."""
    duo = get_executive_duo()
    res = await duo.push_proactive_notification(
        sender=req.sender or "Orion Prime",
        message=req.message,
        category=req.category or "notification",
        options=req.options,
        task_id=req.task_id,
        title=req.title
    )
    return res

