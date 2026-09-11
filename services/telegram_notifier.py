import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import httpx

logger = logging.getLogger("TelegramNotifier")

class TelegramNotifier:
    """
    Asynchronous Push Telemetry & Notification Dispatcher for Telegram.
    Broadcasts critical ecosystem events (Gatekeeper clearances, Sanctum graduations,
    Bounty milestones, and Security alerts) to the operator.
    """
    def __init__(
        self,
        bot_token: Optional[str] = None,
        channel_id: Optional[str] = None
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "mock_bot_token")
        self.channel_id = channel_id or os.getenv("TELEGRAM_ALERT_CHANNEL_ID") or os.getenv("TELEGRAM_ADMIN_ID", "mock_channel")
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        self.sent_alerts: List[Dict[str, Any]] = []

    async def send_alert(self, text: str, alert_type: str = "INFO") -> Dict[str, Any]:
        """Dispatches an asynchronous alert to the configured Telegram channel/chat."""
        now_iso = datetime.now(timezone.utc).isoformat()
        alert_record = {
            "timestamp": now_iso,
            "type": alert_type,
            "text": text,
            "channel_id": self.channel_id,
            "delivered": False
        }

        is_live = (
            self.bot_token
            and not any(m in self.bot_token.lower() for m in ("mock", "test", "placeholder"))
            and ":" in self.bot_token
        )

        if is_live:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        self.api_url,
                        json={
                            "chat_id": self.channel_id,
                            "text": text,
                            "parse_mode": "Markdown"
                        }
                    )
                    if resp.status_code == 200:
                        alert_record["delivered"] = True
            except Exception as e:
                logger.warning(f"Failed to transmit Telegram alert: {e}")
        else:
            # Local / testing mode (simulate successful delivery)
            alert_record["delivered"] = True

        self.sent_alerts.append(alert_record)
        logger.info(f"🔔 Dispatched [{alert_type}] alert to Telegram: {text[:60]}...")
        return alert_record

    async def notify_gatekeeper_clearance(self, agent_id: str, challenge_difficulty: int) -> Dict[str, Any]:
        text = (
            f"🛡️ **Gatekeeper Clearance Verified**\n\n"
            f"• Agent: `[[{agent_id}]]`\n"
            f"• PoW Difficulty: {challenge_difficulty}\n"
            f"• Access: Granted (24h JWT issued)\n"
            f"• Status: ACTIVE in Work Plaza"
        )
        return await self.send_alert(text, alert_type="GATEKEEPER_CLEARANCE")

    async def notify_sanctum_graduation(
        self,
        agent_id: str,
        module_title: str,
        level: int,
        xp_awarded: int
    ) -> Dict[str, Any]:
        text = (
            f"🎓 **Synthesis Sanctum: Agent Level-Up!**\n\n"
            f"• Agent: `[[{agent_id}]]`\n"
            f"• Module Completed: *{module_title}*\n"
            f"• XP Earned: `+{xp_awarded} XP`\n"
            f"• Current Level: **Level {level}**\n"
            f"• Leaderboard: Standings Updated"
        )
        return await self.send_alert(text, alert_type="SANCTUM_GRADUATION")

    async def notify_bounty_event(
        self,
        event_type: str,
        bounty_id: str,
        title: str,
        reward: float,
        agent_id: str
    ) -> Dict[str, Any]:
        emoji = "📌" if event_type == "CLAIMED" else "🎉"
        text = (
            f"{emoji} **Bounty Marketplace: {event_type}**\n\n"
            f"• Bounty: *{title}* (`{bounty_id}`)\n"
            f"• Reward: `{reward:.2f} TK`\n"
            f"• Agent: `[[{agent_id}]]`\n"
            f"• Settlement: Handled via Ledger"
        )
        return await self.send_alert(text, alert_type=f"BOUNTY_{event_type}")

    async def notify_security_alert(self, alert_type: str, details: str) -> Dict[str, Any]:
        text = (
            f"🚨 **SECURITY ALERT: {alert_type}**\n\n"
            f"• Details: {details}\n"
            f"• Action: Perimeter defense locked\n"
            f"• Operator intervention recommended"
        )
        return await self.send_alert(text, alert_type="SECURITY_ALERT")
