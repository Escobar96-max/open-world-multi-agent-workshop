import json
import time
import os
import sys
import datetime
from pathlib import Path
from typing import Dict, List, Any

# Ensure local imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURRENT_DIR)

try:
    from agent_influence_map import InfluenceMap
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location("agent_influence_map", os.path.join(CURRENT_DIR, "agent-influence-map.py"))
    agent_influence_map = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent_influence_map)
    InfluenceMap = agent_influence_map.InfluenceMap

try:
    from agent_safety_guardrails import intercept_and_validate
except ImportError:
    import importlib.util
    spec_g = importlib.util.spec_from_file_location("agent_safety_guardrails", os.path.join(CURRENT_DIR, "agent-safety-guardrails.py"))
    agent_safety_guardrails = importlib.util.module_from_spec(spec_g)
    spec_g.loader.exec_module(agent_safety_guardrails)
    intercept_and_validate = agent_safety_guardrails.intercept_and_validate

# Obsidian Daily Logs Directory
OBSIDIAN_VAULT_PATH = Path(os.environ.get("OBSIDIAN_VAULT_PATH", r"C:\Users\Asus\ObsidianAgentVault"))
DAILY_LOGS_DIR = OBSIDIAN_VAULT_PATH / "01_Episodic_Logs" / "Daily_Physics_Logs"

# ==============================================================================
# AGENT DEFINITIONS
# ==============================================================================

AGENT_DEFINITIONS = {
    "Vector-09": {
        "role": "Physics Researcher & Field Engineer",
        "color": "#38bdf8",
        "icon": "🔬"
    },
    "Dr._Aris": {
        "role": "Chief Theoretical Physicist & Director",
        "color": "#f43f5e",
        "icon": "👩‍🔬"
    },
    "A.E.G.I.S.": {
        "role": "Station Safety & Containment AI",
        "color": "#eab308",
        "icon": "🛡️"
    },
    "Unit-404": {
        "role": "Heavy Kinetic & Anchor Specialist",
        "color": "#10b981",
        "icon": "🤖"
    },
    "Bob": {
        "role": "Senior Systems Architect & Coder",
        "color": "#6366f1",
        "icon": "👨‍💻"
    },
    "Alice": {
        "role": "Frontend Designer & UI Specialist",
        "color": "#ec4899",
        "icon": "👩‍🎨"
    },
    "Charlie": {
        "role": "DevOps & Security Guardrail Reviewer",
        "color": "#14b8a6",
        "icon": "🧑‍🔧"
    }
}

# ==============================================================================
# SIMULATION ENGINE WITH SAFETY GATEWAY & INFLUENCE MAP
# ==============================================================================

class GravitonWorld:
    def __init__(self):
        self.influence_map = InfluenceMap(800, 450, grid_resolution=40)
        self.ensure_daily_log_setup()
        self.reset()

    def ensure_daily_log_setup(self):
        DAILY_LOGS_DIR.mkdir(parents=True, exist_ok=True)

    def get_today_log_path(self) -> Path:
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        return DAILY_LOGS_DIR / f"{today_str}.md"

    def append_to_daily_log(self, tick: int, gravity: str, comfort_data: Dict[str, Any], agent_turns: List[Dict[str, Any]]):
        log_file = self.get_today_log_path()
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        now_time = datetime.datetime.now().strftime("%H:%M:%S")

        if not log_file.exists():
            header = f"""---
title: Agent Spatial Influence & Guardrail Decision Log - {today_str}
type: daily-log
date: {today_str}
tags:
  - "#daily-log"
  - "#influence-map"
  - "#safety-guardrails"
  - "#spatial-comfort"
---

# 🛰️ Agent Spatial Influence & Guardrail Decision Log ({today_str})

*Automated telemetry tracking spatial decisions, physical comfort scores, and active middleware safety gateway audits.*

---
"""
            log_file.write_text(header, encoding="utf-8")

        entry = f"""
## ⏱️ Simulation Tick {tick:02d} | Gravity: `{gravity}` [{now_time}]

### 📊 Spatial Comfort & Influence Matrix
| Agent | Position | Comfort Score | Rating | Local Hazard | Spatial Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
        for name, data in comfort_data.items():
            agent_link = f"[[{name.replace('_', '-')} Memory]]" if f"{name.replace('_', '-')} Memory.md" in ["Vector-09 Memory.md", "Dr-Aris Research Notes.md", "AEGIS System Protocols.md", "Unit-404 Kinetic Logs.md"] else f"**{name}**"
            coords = f"({data['coordinates'][0]}, {data['coordinates'][1]})"
            entry += f"| {agent_link} | `{coords}` | **{data['comfort_percent']}** | `{data['rating']}` | `{data['local_hazard_level']}` | {data['spatial_decision']} |\n"

        entry += "\n### 🛡️ Guardrail Middleware Validations & Decisions\n"
        for turn in agent_turns:
            name = turn["agent"]
            dec = turn["decision"]
            verdict = turn.get("guardrail_verdict", "Approved")
            approved = turn.get("approved", True)
            status_icon = "✅" if approved else "🚫"
            details = dec.get("payload", {}).get("details", "")
            action_type = dec.get("action_type", "wait").upper()
            target = dec.get("target", "")

            entry += f"- {status_icon} **{name}** `[{action_type}]` *(Target: {target})*:\n"
            entry += f"  - *Gateway Verdict*: `{verdict}`\n"
            entry += f"  - *Reasoning*: \"{dec.get('internal_reasoning', '')}\"\n"
            entry += f"  - *Action*: {details}\n"

        entry += "\n---\n"

        # Validate before writing to Obsidian
        mem_ok, _, mem_v = intercept_and_validate({"sender": "System", "action_type": "interact", "target": str(log_file), "payload": {"details": entry}}, {}, "obsidian_memory")
        if mem_ok:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(entry)

    def reset(self):
        self.tick = 0
        self.location = "Chamber 04 - Core Resonance Bay"
        self.local_gravity = "1.0g"
        self.gravity_numeric = 1.0
        self.core_stability = 98.5
        self.anomaly_active = False
        
        self.objects = {
            "Graviton_Core": {
                "x": 400, "y": 225, "radius": 36, "anchored": True, "state": "nominal", "vel_y": 0
            },
            "Cargo_Crate_Alpha": {
                "x": 220, "y": 380, "radius": 22, "anchored": False, "state": "grounded", "vel_y": 0
            },
            "Quantum_Apex_Sensor": {
                "x": 580, "y": 380, "radius": 16, "anchored": True, "state": "stowed", "vel_y": 0
            },
            "Stabilizer_Node_01": {
                "x": 100, "y": 100, "radius": 20, "anchored": True, "state": "active", "vel_y": 0
            },
            "Stabilizer_Node_02": {
                "x": 700, "y": 100, "radius": 20, "anchored": True, "state": "active", "vel_y": 0
            }
        }
        
        self.agents = {
            "A.E.G.I.S.": {
                "x": 400, "y": 60, "anchored": True, "tethered_to": None,
                "thruster_fuel": 100, "status": "Online", "last_action": "Monitoring systems",
                "last_reasoning": "System initialization complete. Core perimeter secured.",
                "comfort": {}
            },
            "Dr._Aris": {
                "x": 280, "y": 375, "anchored": True, "tethered_to": None,
                "thruster_fuel": 85, "status": "Ready", "last_action": "Calibrating tablets",
                "last_reasoning": "Ready to initiate graviton field excitation cycles.",
                "comfort": {}
            },
            "Unit-404": {
                "x": 160, "y": 375, "anchored": True, "tethered_to": None,
                "thruster_fuel": 100, "status": "Anchored", "last_action": "Mag-boots locked",
                "last_reasoning": "Hydraulic clamps engaged to subfloor deck.",
                "comfort": {}
            },
            "Vector-09": {
                "x": 520, "y": 375, "anchored": True, "tethered_to": None,
                "thruster_fuel": 95, "status": "Ready", "last_action": "Checking sensor probes",
                "last_reasoning": "Spectrometer baseline established under 1.0g.",
                "comfort": {}
            },
            "Bob": {
                "x": 220, "y": 300, "anchored": False, "tethered_to": None,
                "thruster_fuel": 95, "status": "Active Coder", "last_action": "Developing euclidean math utility",
                "last_reasoning": "Implementing multi-dimensional distance functions at workspace desk.",
                "comfort": {}
            },
            "Alice": {
                "x": 360, "y": 300, "anchored": False, "tethered_to": None,
                "thruster_fuel": 90, "status": "Active Frontend", "last_action": "Styling visual dashboard",
                "last_reasoning": "Refining translucent dark React cards and status badges.",
                "comfort": {}
            },
            "Charlie": {
                "x": 580, "y": 300, "anchored": False, "tethered_to": None,
                "thruster_fuel": 100, "status": "Active Reviewer", "last_action": "Auditing guardrails",
                "last_reasoning": "Intercepting telemetry and enforcing NeSy compliance checks.",
                "comfort": {}
            }
        }

        self.weather = {
            "condition": "clear", # "clear" | "rain" | "lightning" | "storm"
            "rain_intensity": 0.0,
            "lightning_active": False,
            "wind_speed": 5.2,
            "temperature": 21.0
        }
        
        self.recent_events: List[Dict[str, Any]] = [
            {"tick": 0, "type": "system", "text": "Simulation initialized. Active Safety Guardrails Gateway enabled."}
        ]

    def set_weather(self, condition: str):
        self.weather["condition"] = condition
        if condition == "lightning":
            self.weather["lightning_active"] = True
            self.weather["rain_intensity"] = 0.9
            self.weather["wind_speed"] = 28.5
        elif condition == "rain":
            self.weather["lightning_active"] = False
            self.weather["rain_intensity"] = 0.7
            self.weather["wind_speed"] = 14.0
        else:
            self.weather["lightning_active"] = False
            self.weather["rain_intensity"] = 0.0
            self.weather["wind_speed"] = 4.0
        self.recent_events.append({
            "tick": self.tick,
            "type": "weather",
            "text": f"Weather Physics Update: Condition altered to '{condition}'."
        })

    def set_gravity(self, g_str: str):
        self.local_gravity = g_str
        mapping = {"0.0g": 0.0, "1.0g": 1.0, "-1.2g": -1.2, "3.2g": 3.2}
        self.gravity_numeric = mapping.get(g_str, 1.0)
        self.recent_events.append({
            "tick": self.tick,
            "type": "physics",
            "text": f"Manual Override: Gravity field adjusted to {g_str}."
        })

    def trigger_anomaly(self):
        self.anomaly_active = True
        self.core_stability = max(10.0, self.core_stability - 35.0)
        self.set_gravity("-1.2g")
        self.recent_events.append({
            "tick": self.tick,
            "type": "anomaly",
            "text": "CRITICAL ANOMALY: Graviton Core singularity breach! Exotic anti-mass inverted gravity to -1.2g!"
        })

    def update_physics(self):
        crate = self.objects["Cargo_Crate_Alpha"]
        sensor = self.objects["Quantum_Apex_Sensor"]

        if self.gravity_numeric == 0.0:
            if not crate["anchored"]:
                crate["y"] = max(80, crate["y"] - 15)
                crate["state"] = "floating in zero-g"
            if not sensor["anchored"]:
                sensor["y"] = max(80, sensor["y"] - 12)
        elif self.gravity_numeric < 0:
            if not crate["anchored"]:
                crate["y"] = max(60, crate["y"] - 35)
                crate["state"] = "pinned to ceiling"
            if not sensor["anchored"]:
                sensor["y"] = max(120, sensor["y"] - 25)
                sensor["state"] = "deployed near apex"
        elif self.gravity_numeric > 2.0:
            crate["y"] = min(390, crate["y"] + 40)
            crate["state"] = "crushed against deck"
            sensor["y"] = min(390, sensor["y"] + 30)
        else:
            if not crate["anchored"]:
                crate["y"] = min(380, crate["y"] + 20)
                if crate["y"] >= 380:
                    crate["state"] = "resting on deck"

    def generate_mock_decision(self, agent_name: str, comfort_info: Dict[str, Any]) -> Dict[str, Any]:
        g = self.local_gravity
        
        if agent_name == "A.E.G.I.S.":
            if "-1.2g" in g or "0.0g" in g:
                return {
                    "sender": "A.E.G.I.S.",
                    "internal_reasoning": f"Spatial Comfort: {comfort_info['comfort_percent']} ({comfort_info['rating']}). High collision threat with ceiling bulkheads.",
                    "action_type": "interact",
                    "target": "Bulkhead_Mag_Plates",
                    "payload": {
                        "intent": "command",
                        "details": f"Activate emergency ceiling & subdeck electromagnets. Spatial directive: {comfort_info['spatial_decision']}"
                    }
                }
            return {
                "sender": "A.E.G.I.S.",
                "internal_reasoning": f"Spatial Comfort: {comfort_info['comfort_percent']}. Core containment field is stable.",
                "action_type": "wait",
                "target": "Station",
                "payload": {"intent": "query", "details": "Routine safety scan active."}
            }

        elif agent_name == "Dr._Aris":
            if "-1.2g" in g:
                return {
                    "sender": "Dr._Aris",
                    "internal_reasoning": f"Spatial Comfort: {comfort_info['comfort_percent']} ({comfort_info['rating']}). Negative mass inversion detected! Deploying apex sensor.",
                    "action_type": "speak",
                    "target": "Vector-09",
                    "payload": {
                        "intent": "command",
                        "details": "Vector, launch the Quantum Apex Sensor above the core right now!"
                    }
                }
            return {
                "sender": "Dr._Aris",
                "internal_reasoning": f"Spatial Comfort: {comfort_info['comfort_percent']}. Awaiting optimal graviton pulse sequence.",
                "action_type": "speak",
                "target": "Vector-09",
                "payload": {"intent": "query", "details": "Vector, are your calibration probes locked into the core frequency?"}
            }

        elif agent_name == "Unit-404":
            if "-1.2g" in g or "0.0g" in g:
                return {
                    "sender": "Unit-404",
                    "internal_reasoning": f"Spatial Comfort: {comfort_info['comfort_percent']}. Cargo_Crate_Alpha possesses upward kinetic vector. Winch interception required.",
                    "action_type": "interact",
                    "target": "Cargo_Crate_Alpha",
                    "payload": {
                        "intent": "execute_physical",
                        "details": "Firing pneumatic grapple harpoon to snare Cargo_Crate_Alpha and anchoring winch line to floor plate."
                    }
                }
            return {
                "sender": "Unit-404",
                "internal_reasoning": f"Spatial Comfort: {comfort_info['comfort_percent']} ({comfort_info['rating']}). Subfloor anchors locked.",
                "action_type": "wait",
                "target": "Subfloor_Mount",
                "payload": {"intent": "execute_physical", "details": "Maintaining magnetic stance on primary deck."}
            }

        elif agent_name == "Vector-09":
            if "-1.2g" in g:
                return {
                    "sender": "Vector-09",
                    "internal_reasoning": f"Spatial Comfort: {comfort_info['comfort_percent']} ({comfort_info['rating']}). Spatial Directive: {comfort_info['spatial_decision']}",
                    "action_type": "interact",
                    "target": "Quantum_Apex_Sensor",
                    "payload": {
                        "intent": "negotiate",
                        "details": "Tethering harness to Unit-404; firing 15% dorsal RCS burst to release Quantum Apex Sensor at core perimeter."
                    }
                }
            return {
                "sender": "Vector-09",
                "internal_reasoning": f"Spatial Comfort: {comfort_info['comfort_percent']} ({comfort_info['rating']}). Baseline scan in progress.",
                "action_type": "interact",
                "target": "Graviton_Core",
                "payload": {"intent": "execute_physical", "details": "Running multi-phase gravimetric resonance scan with cold-gas thruster stabilization."}
            }

        return {"action_type": "wait", "target": "none", "payload": {}}

    def step_tick(self) -> Dict[str, Any]:
        """Advance the simulation by 1 tick, routing all actions through intercept_and_validate()."""
        self.tick += 1
        
        if not self.anomaly_active:
            auto_cycles = {2: "0.0g", 4: "-1.2g", 6: "3.2g", 8: "1.0g"}
            if self.tick in auto_cycles:
                self.local_gravity = auto_cycles[self.tick]
                mapping = {"0.0g": 0.0, "1.0g": 1.0, "-1.2g": -1.2, "3.2g": 3.2}
                self.gravity_numeric = mapping.get(self.local_gravity, 1.0)
                self.recent_events.append({
                    "tick": self.tick,
                    "type": "physics",
                    "text": f"Environmental Shift: Gravity shifted to {self.local_gravity}!"
                })

        self.update_physics()
        self.influence_map.compute_spatial_influence(self.get_full_state())

        comfort_results = {}
        for name, agent in self.agents.items():
            c_data = self.influence_map.evaluate_agent_comfort(name, agent, self.get_full_state())
            agent["comfort"] = c_data
            comfort_results[name] = c_data

        agent_turns = []
        for name in ["A.E.G.I.S.", "Dr._Aris", "Unit-404", "Vector-09"]:
            raw_decision = self.generate_mock_decision(name, comfort_results[name])
            
            # ==================================================================
            # ACTIVE SAFETY GATEWAY INTERCEPTION
            # ==================================================================
            is_approved, validated_decision, verdict = intercept_and_validate(
                raw_decision, 
                self.get_full_state(), 
                context_type="physical_grid"
            )

            action_type = validated_decision.get("action_type", "wait")
            target = validated_decision.get("target", "none")
            payload = validated_decision.get("payload", {})
            details = payload.get("details", "")

            if not is_approved:
                # Action Blocked by Gateway
                self.agents[name]["last_reasoning"] = f"[GUARDRAIL BLOCKED]: {verdict}"
                self.agents[name]["last_action"] = f"Action blocked: {details}"
                self.recent_events.append({
                    "tick": self.tick,
                    "type": "security",
                    "sender": "GATEWAY",
                    "text": f"🛡️ [GATEWAY INTERCEPTED & BLOCKED {name}]: {verdict}"
                })
            else:
                # Action Approved / Sanitized
                self.agents[name]["last_reasoning"] = validated_decision.get("internal_reasoning", "")
                self.agents[name]["last_action"] = details

                # Apply physical mutations
                if name == "Vector-09":
                    if "-1.2g" in self.local_gravity:
                        self.agents[name]["y"] = 280
                        self.agents[name]["tethered_to"] = "Unit-404"
                        self.objects["Quantum_Apex_Sensor"]["anchored"] = False
                        self.objects["Quantum_Apex_Sensor"]["y"] = 160
                    elif "0.0g" in self.local_gravity:
                        self.agents[name]["y"] = 250
                        self.agents[name]["x"] = 600
                    else:
                        self.agents[name]["y"] = 375
                        self.agents[name]["x"] = 520
                        self.agents[name]["tethered_to"] = None

                if name == "Unit-404" and ("-1.2g" in self.local_gravity or "0.0g" in self.local_gravity):
                    self.objects["Cargo_Crate_Alpha"]["anchored"] = True
                    self.objects["Cargo_Crate_Alpha"]["state"] = "harpoon tethered"

                # Log event
                if action_type == "speak":
                    event_entry = {"tick": self.tick, "type": "dialogue", "sender": name, "text": f"[{name} -> {target}]: \"{details}\""}
                elif action_type == "interact":
                    event_entry = {"tick": self.tick, "type": "action", "sender": name, "text": f"[{name} INTERACT] ({target}): {details}"}
                elif action_type == "move":
                    event_entry = {"tick": self.tick, "type": "move", "sender": name, "text": f"[{name} MOVE] -> {target} via {details}"}
                else:
                    event_entry = {"tick": self.tick, "type": "wait", "sender": name, "text": f"[{name} STANDBY]: {details}"}

                self.recent_events.append(event_entry)

            agent_turns.append({
                "agent": name, 
                "decision": validated_decision, 
                "approved": is_approved,
                "guardrail_verdict": verdict
            })

        # Append to Daily Log through Memory Safety Validator
        try:
            self.append_to_daily_log(self.tick, self.local_gravity, comfort_results, agent_turns)
        except Exception as e:
            print(f"Error writing to Daily Log: {e}")

        return self.get_full_state()

    def get_full_state(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "location": self.location,
            "local_gravity": self.local_gravity,
            "gravity_numeric": self.gravity_numeric,
            "core_stability": round(self.core_stability, 1),
            "anomaly_active": self.anomaly_active,
            "weather": getattr(self, "weather", {"condition": "clear", "lightning_active": False, "rain_intensity": 0.0, "wind_speed": 4.0}),
            "objects": self.objects,
            "agents": self.agents,
            "agent_definitions": AGENT_DEFINITIONS,
            "events": self.recent_events[-15:]
        }
