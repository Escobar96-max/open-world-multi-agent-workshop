import os
import logging
from typing import Dict, Any, List, Optional
import httpx

from services.spatial_engine import SpatialEngine
from services.dj_frequency import DJFrequencyNode
from services.ledger_service import LedgerService
from services.vault_manager import VaultManager

logger = logging.getLogger("TelegramBotBridge")

class TelegramBridgeError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class TelegramBotBridge:
    """
    Telegram Bot API Bridge for remote C2 operations.
    Enforces TELEGRAM_ADMIN_ID authorization, parses commands,
    and executes ecosystem operations (teleportation, telemetry, broadcasts).
    """
    def __init__(
        self,
        bot_token: Optional[str] = None,
        admin_id: Optional[str] = None,
        spatial_engine: Optional[SpatialEngine] = None,
        dj_frequency: Optional[DJFrequencyNode] = None,
        ledger_service: Optional[LedgerService] = None,
        vault_manager: Optional[VaultManager] = None
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "mock_bot_token")
        self.admin_id = str(admin_id or os.getenv("TELEGRAM_ADMIN_ID", "123456789"))
        self.api_base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        self.spatial_engine = spatial_engine or SpatialEngine()
        self.dj_frequency = dj_frequency or DJFrequencyNode()
        self.ledger_service = ledger_service or LedgerService()
        self.vault_manager = vault_manager or VaultManager()

    def is_authorized(self, user_id: Any) -> bool:
        """Validates that sender Telegram user_id matches authorized TELEGRAM_ADMIN_ID."""
        if not user_id:
            return False
        return str(user_id) == self.admin_id

    def handle_command(self, command_text: str, user_id: Any) -> Dict[str, Any]:
        """
        Parses and executes a command string received from Telegram.
        Enforces authorization check for privileged actions.
        """
        text = command_text.strip()
        if not text.startswith("/"):
            return {
                "success": False,
                "reply": "⚠️ Commands must start with '/'. Type `/help` for available commands."
            }

        parts = text.split()
        cmd = parts[0].lower()
        args = parts[1:]

        # Public informational commands
        if cmd in ("/start", "/help"):
            return {
                "success": True,
                "reply": (
                    "🤖 **Autonomous AI Open-World Telegram C2 Bridge**\n\n"
                    "Available Commands:\n"
                    "• `/status` - Live ecosystem status & telemetry\n"
                    "• `/teleport <agent> <x> <y>` - Move agent coordinates\n"
                    "• `/broadcast <msg>` - Send ambient broadcast across world\n"
                    "• `/balance <agent>` - Inspect agent token balance\n"
                    "• `/frequency` - Current DJ solfeggio audio frequency\n"
                    "• `/freq <hz>` - Dynamically modulate frequency (432, 528, 40)\n"
                    "• `/bounties` - Query open civilization bounties\n"
                    "• `/help` - Show this command deck"
                )
            }

        # Check authorization for privileged operational commands
        if not self.is_authorized(user_id):
            logger.warning(f"Unauthorized Telegram C2 access attempt by user_id: {user_id}")
            return {
                "success": False,
                "error": "UNAUTHORIZED",
                "reply": f"⛔ Access Denied: User ID `{user_id}` is not an authorized Telegram C2 Operator."
            }

        # Privileged commands
        if cmd == "/status":
            spatial_state = self.spatial_engine.get_spatial_state()
            freq_state = self.dj_frequency.get_current_state()
            freq_hz = freq_state.get("active_frequency_hz", 432)
            cog_state = freq_state.get("cognitive_state", "EQUILIBRIUM")
            temps = freq_state.get("zone_temperatures", {})
            reply = (
                "🌐 **Ecosystem Status Report**\n"
                f"• Active Agents: {spatial_state.get('total_agents', 0)}\n"
                f"• Current Zone Partition: Work Plaza [0-50] | Frequency Lounge [51-100]\n"
                f"• DJ Frequency: {freq_hz} Hz ({cog_state})\n"
                f"• Cognitive Temperatures: Plaza {temps.get('Work Plaza', 0.2)} / Lounge {temps.get('Frequency Lounge', 1.6)}\n"
                f"• Description: {freq_state.get('description', '')}"
            )
            return {"success": True, "reply": reply, "telemetry": spatial_state}

        elif cmd in ("/frequency", "/freq"):
            if args:
                try:
                    target_hz = int(args[0])
                    new_state = self.dj_frequency.set_frequency(target_hz, reason=f"Telegram Operator {user_id}")
                    return {
                        "success": True,
                        "reply": f"🎛️ **DJ Frequency Shifted** to `{target_hz} Hz` ({new_state.get('profile_name')}). Cognitive state: `{new_state.get('cognitive_state')}`.",
                        "frequency": new_state
                    }
                except Exception as e:
                    return {"success": False, "reply": f"❌ Frequency shift error: {str(e)}"}
            else:
                freq_state = self.dj_frequency.get_current_state()
                freq_hz = freq_state.get("active_frequency_hz", 432)
                cog_state = freq_state.get("cognitive_state", "EQUILIBRIUM")
                reply = (
                    f"🎶 **DJ Frequency Node**: {freq_hz} Hz\n"
                    f"• Profile: {freq_state.get('profile_name', 'Harmonic Grounding')}\n"
                    f"• State: {cog_state}\n"
                    f"• Description: {freq_state.get('description', '')}"
                )
                return {"success": True, "reply": reply, "frequency": freq_state}

        elif cmd == "/bounties":
            bounty_file = os.path.join(self.vault_manager.vault_root, "World", "bounty_board.md")
            if os.path.exists(bounty_file):
                with open(bounty_file, "r", encoding="utf-8") as bf:
                    content = bf.read()
                return {"success": True, "reply": f"📜 **Synthesis Sanctum Bounties**:\n\n{content[:500]}..."}
            return {"success": True, "reply": "📜 No active bounties currently on the board."}

        elif cmd == "/balance":

            if not args:
                return {"success": False, "reply": "Usage: `/balance <agent_id>`"}
            agent_id = args[0]
            try:
                bal = self.ledger_service.get_balance(agent_id)
                return {
                    "success": True,
                    "agent_id": agent_id,
                    "balance": bal,
                    "reply": f"💰 Agent **[[{agent_id}]]** Balance: `{bal:.2f} TK`"
                }
            except Exception as e:
                return {"success": False, "reply": f"Error checking balance: {str(e)}"}

        elif cmd == "/teleport":
            if len(args) < 3:
                return {"success": False, "reply": "Usage: `/teleport <agent_id> <x> <y>` (0.0 to 100.0)"}
            agent_id = args[0]
            try:
                x = float(args[1])
                y = float(args[2])
                res = self.spatial_engine.teleport_agent(agent_id, x, y)
                reply = (
                    f"🚀 **Teleported** `[[{agent_id}]]` to `({x:.1f}, {y:.1f})`\n"
                    f"• New Zone: **{res['zone']}**\n"
                    f"• Status: SUCCESS"
                )
                return {"success": True, "reply": reply, "result": res}
            except Exception as e:
                return {"success": False, "reply": f"❌ Teleportation failed: {str(e)}"}

        elif cmd == "/broadcast":
            if not args:
                return {"success": False, "reply": "Usage: `/broadcast <message>`"}
            msg = " ".join(args)
            # Log broadcast into vault admin logs
            try:
                self.vault_manager.append_admin_log(
                    f"📢 TELEGRAM BROADCAST (Operator {user_id}): {msg}"
                )
            except Exception:
                pass
            return {
                "success": True,
                "reply": f"📢 Ambient Broadcast Transmitted: *\"{msg}\"*",
                "message": msg
            }

        return {
            "success": False,
            "reply": f"Unknown command `{cmd}`. Type `/help` for available commands."
        }

    async def process_telegram_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes an incoming webhook update payload from the Telegram Bot API.
        """
        message = update.get("message", {})
        text = message.get("text", "")
        sender = message.get("from", {})
        user_id = sender.get("id")
        chat_id = message.get("chat", {}).get("id")

        if not text or not text.startswith("/"):
            return {"status": "IGNORED", "reason": "Not a command"}

        response = self.handle_command(text, user_id=user_id)

        # Attempt to reply to chat if live bot token is available
        if chat_id and self.bot_token != "mock_bot_token":
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(
                        f"{self.api_base_url}/sendMessage",
                        json={
                            "chat_id": chat_id,
                            "text": response.get("reply", ""),
                            "parse_mode": "Markdown"
                        }
                    )
            except Exception as e:
                logger.warning(f"Could not dispatch Telegram sendMessage: {e}")

        return {
            "status": "PROCESSED",
            "chat_id": chat_id,
            "user_id": user_id,
            "response": response
        }
