import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException

from services.bot_bridge import TelegramBotBridge
from services.telegram_notifier import TelegramNotifier

logger = logging.getLogger("TelegramRouter")

router = APIRouter(prefix="/api/v1/telegram", tags=["Telegram Bot Bridge & Push Telemetry"])

bot_bridge = TelegramBotBridge()
notifier = TelegramNotifier()

@router.post("/webhook", summary="Telegram Webhook Endpoint")
async def telegram_webhook(request: Request):
    """
    Receives incoming updates from Telegram Bot API webhook, executes C2 commands,
    and returns response.
    """
    try:
        update_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    result = await bot_bridge.process_telegram_update(update_data)
    return result

@router.get("/status", summary="Telegram Bot Bridge Status")
async def telegram_status():
    """Returns the operational status of the Telegram Bot Bridge."""
    return {
        "status": "ONLINE",
        "bot_configured": bot_bridge.bot_token != "mock_bot_token",
        "admin_id_configured": bot_bridge.admin_id != "123456789",
        "recent_alerts_sent": len(notifier.sent_alerts),
        "supported_commands": [
            "/start", "/help", "/status", "/frequency", "/balance", "/teleport", "/broadcast"
        ]
    }
