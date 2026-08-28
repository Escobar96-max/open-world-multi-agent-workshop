import math
import sys
from typing import Dict, List, Tuple, Any

class InfluenceMap:
    """
    InfluenceMap: Computes continuous 2D spatial influence fields, hazard gradients,
    anchor attractors, and dynamic physical comfort values for autonomous agents
    in an anti-gravity physics simulation.
    """
    def __init__(self, width: int = 800, height: int = 450, grid_resolution: int = 40):
        self.width = width
        self.height = height
        self.resolution = grid_resolution
        self.cols = width // grid_resolution
        self.rows = height // grid_resolution
        
        # 2D Grid matrices (pure Python lists)
        self.hazard_map = [[0.0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.anchor_map = [[0.0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.comfort_map = [[1.0 for _ in range(self.cols)] for _ in range(self.rows)]

    def reset_fields(self):
        for r in range(self.rows):
            for c in range(self.cols):
                self.hazard_map[r][c] = 0.0
                self.anchor_map[r][c] = 0.0
                self.comfort_map[r][c] = 0.0

    def calculate_distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    def compute_spatial_influence(self, world_state: Dict[str, Any]):
        """
        Updates the 2D influence grid based on objects, core status, and gravity.
        """
        self.reset_fields()
        gravity_num = world_state.get("gravity_numeric", 1.0)
        objects = world_state.get("objects", {})
        anomaly_active = world_state.get("anomaly_active", False)

        # 1. Graviton Core Hazard & Radiative Field
        core = objects.get("Graviton_Core", {"x": 400, "y": 225})
        core_intensity = 3.5 if anomaly_active else (2.2 if abs(gravity_num - 1.0) > 0.5 else 0.8)

        # 2. Unanchored Kinetic Hazards (e.g. drifting crates)
        hazards = []
        for obj_name, obj in objects.items():
            if "Crate" in obj_name and not obj.get("anchored", True):
                hazard_weight = 2.8 if abs(gravity_num) > 0.5 else 1.2
                hazards.append((obj["x"], obj["y"], hazard_weight))

        # 3. Anchor & Stabilizer Attractors
        anchors = []
        for obj_name, obj in objects.items():
            if "Stabilizer" in obj_name or "Bulkhead" in obj_name:
                anchors.append((obj["x"], obj["y"], 2.2))

        # Populate Grid
        for r in range(self.rows):
            for c in range(self.cols):
                gx = c * self.resolution + self.resolution / 2
                gy = r * self.resolution + self.resolution / 2

                # Core hazard gradient
                d_core = self.calculate_distance(gx, gy, core["x"], core["y"])
                core_falloff = core_intensity / (1.0 + (d_core / 120.0) ** 2)
                self.hazard_map[r][c] += core_falloff

                # Kinetic hazard proximity
                for hx, hy, hw in hazards:
                    dh = self.calculate_distance(gx, gy, hx, hy)
                    self.hazard_map[r][c] += hw / (1.0 + (dh / 80.0) ** 2)

                # Anchor attractor bonus
                for ax, ay, aw in anchors:
                    da = self.calculate_distance(gx, gy, ax, ay)
                    self.anchor_map[r][c] += aw / (1.0 + (da / 140.0) ** 2)

                # Compute baseline comfort: High anchor bonus, Low hazard, Gravity stability
                gravity_stress = abs(gravity_num - 1.0) * 0.35
                comfort = 1.0 + (self.anchor_map[r][c] * 0.45) - (self.hazard_map[r][c] * 0.55) - gravity_stress
                self.comfort_map[r][c] = max(0.05, min(1.0, comfort))

    def evaluate_agent_comfort(self, agent_name: str, agent_data: Dict[str, Any], world_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates exact physical comfort score and spatial decision gradient for an agent.
        """
        ax = agent_data.get("x", 400)
        ay = agent_data.get("y", 375)
        anchored = agent_data.get("anchored", True)
        tethered = agent_data.get("tethered_to") is not None
        g_num = world_state.get("gravity_numeric", 1.0)
        
        c_col = min(self.cols - 1, max(0, int(ax // self.resolution)))
        r_row = min(self.rows - 1, max(0, int(ay // self.resolution)))

        base_comfort = self.comfort_map[r_row][c_col]
        local_hazard = self.hazard_map[r_row][c_col]
        local_anchor = self.anchor_map[r_row][c_col]

        # Adjust for agent-specific physical state
        if not anchored and not tethered:
            if abs(g_num - 1.0) > 0.2:
                base_comfort *= 0.45  # Heavy penalty for unanchored drift in abnormal gravity
        elif tethered:
            base_comfort = min(1.0, base_comfort * 1.35)  # Tether safety bonus

        comfort_score = round(max(0.05, min(1.0, base_comfort)), 3)

        # Determine Comfort Level & Spatial Recommendation
        if comfort_score >= 0.75:
            rating = "Optimal Stability"
            status_desc = f"Environmentally secure. Thruster loads nominal at ({ax:.0f}, {ay:.0f})."
            decision = "Hold current spatial coordinates for optimal sensor telemetry alignment."
        elif comfort_score >= 0.45:
            rating = "Moderate Stress"
            status_desc = f"Experiencing gravitational delta ({g_num}g). Moderate hazard proximity."
            decision = "Engage magnetic boot clamps or tether to heavy structural chassis."
        else:
            rating = "Critical Spatial Hazard"
            d_to_core = self.calculate_distance(ax, ay, 400, 225)
            status_desc = f"Severe gravitational drift and radiation flux. Core distance = {d_to_core:.1f}px."
            decision = "Immediate evasive RCS thrust burst toward nearest Stabilizer Node."

        return {
            "agent": agent_name,
            "coordinates": (int(ax), int(ay)),
            "comfort_score": comfort_score,
            "comfort_percent": f"{comfort_score * 100:.1f}%",
            "rating": rating,
            "local_hazard_level": round(local_hazard, 2),
            "anchor_proximity_bonus": round(local_anchor, 2),
            "status_description": status_desc,
            "spatial_decision": decision
        }
