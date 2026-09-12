import os
import re
import secrets
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from .vault_manager import VaultManager, VaultSecurityError

class ConsoleSecurityError(Exception):
    def __init__(self, message: str = "Unauthorized: Invalid or missing ADMIN_SECRET_KEY.", status_code: int = 401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class ConsoleC2Service:
    def __init__(
        self,
        vault_manager: Optional[VaultManager] = None,
        admin_key: Optional[str] = None,
        spatial_engine: Optional[Any] = None,
        world_engine: Optional[Any] = None,
        dj_frequency: Optional[Any] = None
    ):
        self.vault = vault_manager or VaultManager()
        self.admin_key = admin_key or os.getenv("ADMIN_SECRET_KEY", "op_secret_master_key_9921")
        self.spatial = spatial_engine
        self.world = world_engine
        self.dj_frequency = dj_frequency

    def set_world_engine(self, world_engine: Any) -> None:
        self.world = world_engine

    def set_dj_frequency(self, dj_frequency: Any) -> None:
        self.dj_frequency = dj_frequency

    def verify_admin_key(self, provided_key: Optional[str]) -> None:
        if not provided_key or not secrets.compare_digest(provided_key, self.admin_key):
            raise ConsoleSecurityError("Unauthorized: Missing or invalid ADMIN_SECRET_KEY.")

    def parse_and_execute(
        self,
        command: str,
        target_agent: Optional[str] = None,
        operator_id: str = "Operator_Root"
    ) -> Dict[str, Any]:
        """
        Parses either a slash command (/teleport, /train) or a natural language directive.
        """
        if not command or not command.strip():
            raise ValueError("Command cannot be empty.")

        cmd = command.strip()
        now_iso = datetime.now(timezone.utc).isoformat()

        if cmd.startswith("/"):
            result = self._execute_slash_command(cmd, operator_id)
        else:
            if not target_agent:
                raise ValueError("Target agent must be specified for natural language directives.")
            result = self._inject_directive_memory(target_agent, cmd, operator_id)

        # Append to World/admin_logs.md
        status_str = "SUCCESS" if result.get("status") == "SUCCESS" else "FAILED"
        agent_target = target_agent or result.get("agent_id", "N/A")
        safe_cmd = cmd.replace("\r", " ").replace("\n", " ").replace("|", "\\|")
        safe_operator = str(operator_id).replace("\r", " ").replace("\n", " ").replace("|", "\\|")
        safe_target = str(agent_target).replace("\r", " ").replace("\n", " ").replace("|", "\\|")
        log_entry = f"| {now_iso} | {safe_operator} | `{safe_cmd}` | {safe_target} | {status_str} |"
        self.vault.append_world_log("admin_logs", log_entry)

        return result

    def _execute_slash_command(self, slash_cmd: str, operator_id: str) -> Dict[str, Any]:
        parts = slash_cmd.split()
        keyword = parts[0].lower()

        if keyword == "/teleport":
            # Syntax: /teleport <agent_id> <x> <y>
            if len(parts) != 4:
                return {
                    "status": "ERROR",
                    "command": slash_cmd,
                    "error": "Syntax error. Expected: /teleport <agent_id> <x> <y>"
                }
            
            agent_id = parts[1]
            try:
                x = float(parts[2])
                y = float(parts[3])
            except ValueError:
                return {"status": "ERROR", "error": "Coordinates x and y must be numerical values."}

            if not (0.0 <= x <= 100.0 and 0.0 <= y <= 100.0):
                return {"status": "ERROR", "error": "Coordinates out of bounds. Matrix bounded to [0,0] to [100,100]."}

            # Update agent profile
            try:
                fm, body = self.vault.get_agent_profile(agent_id)
            except FileNotFoundError:
                fm = {"agent_id": agent_id, "name": agent_id}
                body = f"# Profile for {agent_id}\n\nAuto-created via C2 Teleport."

            fm["coordinates"] = [x, y]
            # Check zone
            if x <= 50.0 and y <= 50.0:
                fm["zone"] = "Work Plaza"
                fm["temperature"] = 0.2
            else:
                fm["zone"] = "Frequency Lounge & Sanctum"
                fm["temperature"] = 1.6

            self.vault.write_agent_profile(agent_id, fm, body)
            if self.spatial:
                try:
                    self.spatial.teleport_agent(agent_id, x, y)
                except Exception:
                    pass

            # Record memory of teleportation
            mem_id = f"mem_tp_{int(datetime.now(timezone.utc).timestamp())}_{secrets.token_hex(2)}"
            self.vault.add_agent_memory(
                agent_id=agent_id,
                memory_id=mem_id,
                content=f"Operator executed /teleport to coordinates [{x}, {y}]. Shifted zone to {fm['zone']}.",
                importance=8,
                source="Operator_C2",
                tags=["teleport", "c2_command"]
            )

            return {
                "status": "SUCCESS",
                "command": "/teleport",
                "agent_id": agent_id,
                "new_coordinates": [x, y],
                "zone": fm["zone"],
                "temperature": fm["temperature"]
            }

        elif keyword == "/train":
            # Syntax: /train <agent_id> <curriculum>
            if len(parts) < 3:
                return {
                    "status": "ERROR",
                    "command": slash_cmd,
                    "error": "Syntax error. Expected: /train <agent_id> <curriculum>"
                }

            agent_id = parts[1]
            curriculum = " ".join(parts[2:])

            mem_id = f"mem_train_{int(datetime.now(timezone.utc).timestamp())}_{secrets.token_hex(2)}"
            self.vault.add_agent_memory(
                agent_id=agent_id,
                memory_id=mem_id,
                content=f"Operator dispatched /train directive with curriculum: '{curriculum}'. Initiating Soup Zero preparation.",
                importance=9,
                source="Operator_C2",
                tags=["training", "soup_zero", "curriculum"]
            )

            return {
                "status": "SUCCESS",
                "command": "/train",
                "agent_id": agent_id,
                "curriculum": curriculum,
                "message": f"Training curriculum '{curriculum}' assigned to {agent_id}."
            }

        elif keyword == "/gravity":
            # Syntax: /gravity <value> (e.g. 0.0g, 0.4g, 1.0g, -1.2g)
            if len(parts) < 2:
                return {"status": "ERROR", "command": slash_cmd, "error": "Syntax: /gravity <0.0g|0.4g|1.0g|-1.2g>"}
            val = parts[1]
            if self.world and hasattr(self.world, "set_gravity"):
                self.world.set_gravity(val)
                return {"status": "SUCCESS", "command": "/gravity", "gravity": val, "message": f"World gravity shifted to {val}."}
            return {"status": "SUCCESS", "command": "/gravity", "gravity": val, "message": f"Gravity directive recorded: {val}"}

        elif keyword == "/weather":
            # Syntax: /weather <condition> (e.g. clear, rain, storm, rad)
            if len(parts) < 2:
                return {"status": "ERROR", "command": slash_cmd, "error": "Syntax: /weather <clear|rain|storm|rad>"}
            cond = parts[1].lower()
            if self.world and hasattr(self.world, "set_weather"):
                self.world.set_weather(cond)
                return {"status": "SUCCESS", "command": "/weather", "weather": cond, "message": f"Atmospheric condition shifted to {cond}."}
            return {"status": "SUCCESS", "command": "/weather", "weather": cond, "message": f"Weather directive recorded: {cond}"}

        elif keyword == "/step":
            res = {}
            if self.spatial and hasattr(self.spatial, "step_simulation"):
                res["spatial"] = self.spatial.step_simulation(delta_time=1.0)
            if self.world and hasattr(self.world, "step_tick"):
                res["world"] = self.world.step_tick()
            return {"status": "SUCCESS", "command": "/step", "result": res, "message": "Advanced world & spatial simulation 1 tick."}

        elif keyword == "/anomaly":
            if self.world and hasattr(self.world, "trigger_anomaly"):
                self.world.trigger_anomaly()
                return {"status": "SUCCESS", "command": "/anomaly", "message": "Singularity anomaly triggered in physics core."}
            return {"status": "SUCCESS", "command": "/anomaly", "message": "Anomaly directive logged."}

        elif keyword == "/freq":
            if len(parts) < 2:
                return {"status": "ERROR", "command": slash_cmd, "error": "Syntax: /freq <432|528|40>"}
            try:
                freq = int(parts[1])
            except ValueError:
                return {"status": "ERROR", "error": "Frequency must be an integer (e.g. 432, 528, 40)."}
            if self.dj_frequency and hasattr(self.dj_frequency, "set_frequency"):
                state = self.dj_frequency.set_frequency(freq, reason="C2 /freq command")
                return {"status": "SUCCESS", "command": "/freq", "frequency_state": state, "message": f"DJ frequency shifted to {freq}Hz."}
            return {"status": "SUCCESS", "command": "/freq", "frequency": freq, "message": f"Frequency directive set to {freq}Hz."}

        elif keyword == "/consolidate":
            try:
                from agent_memory_consolidator import MemoryConsolidator
                cons = MemoryConsolidator()
                res = cons.run_consolidation_cycle()
                return {"status": "SUCCESS", "command": "/consolidate", "consolidation": res}
            except Exception as e:
                return {"status": "ERROR", "command": "/consolidate", "error": str(e)}

        elif keyword == "/ask":
            # Syntax: /ask <agent_id> <prompt...>
            if len(parts) < 3:
                return {
                    "status": "ERROR",
                    "command": slash_cmd,
                    "error": "Syntax error. Expected: /ask <agent_id> <query>"
                }
            agent_id = parts[1]
            query = " ".join(parts[2:])
            self.vault.validate_identifier(agent_id)

            from services.ollama_client import OllamaClient
            ollama = OllamaClient()
            reply = None
            try:
                if ollama.is_available():
                    system = (
                        f"You are {agent_id}, an autonomous AI entity in the open-world multi-agent civilization. "
                        f"Respond directly to the human operator with intelligence and authentic character."
                    )
                    reply = ollama.generate(prompt=query, system=system, temperature=0.7, max_tokens=150)
                    if not reply:
                        reply = f"Transmission received from Operator. Processing inquiry regarding '{query}'."
            except Exception as e:
                logger.warning(f"Ollama interrogation failed: {e}")

            if not reply:
                reply = f"Local LLM offline. {agent_id} acknowledges directive: '{query}'."

            # Log to agent memory
            mem_id = f"mem_ask_{int(datetime.now(timezone.utc).timestamp())}_{secrets.token_hex(2)}"
            self.vault.add_agent_memory(
                agent_id=agent_id,
                memory_id=mem_id,
                content=f"Operator asked: '{query}'. {agent_id} responded: '{reply}'.",
                importance=8,
                source="Operator_Ask",
                tags=["c2_dialogue", "operator_inquiry"]
            )

            return {
                "status": "SUCCESS",
                "command": "/ask",
                "agent_id": agent_id,
                "query": query,
                "response": reply,
                "message": f"[{agent_id}]: {reply}"
            }

        else:
            return {
                "status": "ERROR",
                "command": slash_cmd,
                "error": f"Unknown slash command: '{keyword}'. Available: /teleport, /train, /gravity, /weather, /step, /anomaly, /freq, /consolidate, /ask"
            }

    def _inject_directive_memory(self, agent_id: str, directive: str, operator_id: str) -> Dict[str, Any]:
        """
        Injects a natural language directive directly into /vault/Agents/{agent_id}/memories/
        with Importance 10/10 and Source: Operator.
        """
        self.vault.validate_identifier(agent_id)
        mem_id = f"mem_op_{int(datetime.now(timezone.utc).timestamp())}_{secrets.token_hex(2)}"
        
        mem_file = self.vault.add_agent_memory(
            agent_id=agent_id,
            memory_id=mem_id,
            content=f"OPERATOR DIRECTIVE: {directive}",
            importance=10,
            source=operator_id,
            tags=["directive", "operator_priority_10", "override"]
        )

        return {
            "status": "SUCCESS",
            "type": "NATURAL_LANGUAGE_DIRECTIVE",
            "agent_id": agent_id,
            "memory_id": mem_id,
            "importance": 10,
            "source": operator_id,
            "memory_file": str(mem_file),
            "directive": directive
        }
