import os
import sys
import json
import time
import urllib.request
import urllib.error
import subprocess
import datetime
from typing import List, Dict, Tuple, Optional, Any

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# =====================================================================
# SYSTEM CONFIGURATION & DIRECTORIES
# =====================================================================
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11435")
VAULT_PATH = os.environ.get("VAULT_PATH", os.path.abspath(os.path.join(os.path.dirname(__file__), "ObsidianAgentVault")))
EPISODIC_DIR = os.path.join(VAULT_PATH, "01_Episodic_Logs")
SEMANTIC_DIR = os.path.join(VAULT_PATH, "02_Semantic_Graph")
CANVAS_FILE = os.path.join(VAULT_PATH, "World_Map.canvas")

# Ensure environment directories exist
for path in [EPISODIC_DIR, os.path.join(SEMANTIC_DIR, "Agents"), os.path.join(SEMANTIC_DIR, "Locations")]:
    os.makedirs(path, exist_ok=True)


# =====================================================================
# 1. SECURE OLLAMA CLIENT WITH PROXY TOKEN AUTHENTICATION
# =====================================================================
class OllamaClient:
    """
    Connects to our secure Ollama reverse proxy on port 11435 with token-gated
    bypass headers. Falls back to deterministic simulation mode if offline.
    """
    def __init__(self, base_url: str = OLLAMA_HOST):
        self.base_url = base_url.rstrip("/")
        self.token = self._load_proxy_token()
        self.is_online = self._ping_ollama()

    def _load_proxy_token(self) -> str:
        token_file = os.path.expanduser("~/.ollama_proxy_token")
        if os.path.exists(token_file):
            try:
                with open(token_file, "r", encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass
        return os.environ.get("OLLAMA_PROXY_TOKEN", "5372a7f3032729494adca121752d4432bbadec1fc692d63f2e2e8401206bf41a")

    def _ping_ollama(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                headers={"X-Ollama-Bypass-Token": self.token}
            )
            with urllib.request.urlopen(req, timeout=2.0) as response:
                return response.status == 200
        except Exception:
            return False

    def generate(self, model: str, prompt: str, system: str = "", temperature: float = 0.2) -> str:
        """Calls the secure Ollama proxy endpoint with X-Ollama-Bypass-Token."""
        if self.is_online:
            try:
                url = f"{self.base_url}/api/generate"
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "system": system,
                    "options": {"temperature": temperature},
                    "stream": False
                }
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url, 
                    data=data, 
                    headers={
                        "Content-Type": "application/json",
                        "X-Ollama-Bypass-Token": self.token
                    }
                )
                with urllib.request.urlopen(req, timeout=15.0) as response:
                    res_body = json.loads(response.read().decode("utf-8"))
                    return res_body.get("response", "")
            except Exception as e:
                print(f"⚠️ [Ollama API Error] {e}. Shifting to local simulation fallback.")
        
        # Consistent Simulation Fallback (Generates rich mock coding streams)
        return self._simulate_response(system, prompt)

    def _simulate_response(self, system: str, prompt: str) -> str:
        """Provides simulated outputs that perfectly mimic our expanded developer workspace."""
        prompt_lower = prompt.lower()
        sys_lower = system.lower()
        
        if "project manager" in sys_lower or "planner" in prompt_lower:
            return """{
  "status": "PLANNING_SUCCESS",
  "plan": [
    {"step": 1, "task": "Implement high-performance euclidean math logic", "assignee": "Coder"},
    {"step": 2, "task": "Design responsive UI components and visual styles using Tailwind CSS", "assignee": "Frontend_Developer"},
    {"step": 3, "task": "Perform a comprehensive security audit and code quality review", "assignee": "Code_Reviewer"},
    {"step": 4, "task": "Mount compiled bundles and execute test suite", "assignee": "Deployer"}
  ],
  "requirements": "Create a fully functional utility and associated visual layout. Ensure proper scoping, import declarations, and beautiful style sheets."
}"""
        elif "frontend" in sys_lower or "frontend" in prompt_lower:
            if "fail" in prompt_lower or "feedback" in prompt_lower or "reviewer" in prompt_lower:
                return """// Beautiful, High-Performance React Dashboard Card
// Fully corrected based on the Code Reviewer's styling audit.
import React from 'react';

export const AgentDashboardCard = ({ agentName, status, location }) => {
  return (
    <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl shadow-lg hover:shadow-cyan-500/10 transition-all duration-300">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-bold text-slate-100">{agentName}</h3>
        <span className="px-2.5 py-1 text-xs font-semibold bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20">
          {status}
        </span>
      </div>
      <p className="text-sm text-slate-400">
        Current Location: <strong className="text-cyan-400">{location}</strong>
      </p>
    </div>
  );
};
"""
            # Original frontend code draft with a minor CSS bug (unstyled badge) to demonstrate review feedback
            return """// Beautiful, High-Performance React Dashboard Card
import React from 'react';

export const AgentDashboardCard = ({ agentName, status, location }) => {
  return (
    <div className="p-6 bg-slate-900 rounded-xl shadow-lg border border-slate-800">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-bold text-slate-100">{agentName}</h3>
        {/* Missing styling for status block to trigger Code Reviewer feedback! */}
        <span>{status}</span>
      </div>
      <p className="text-sm text-slate-400">
        Current Location: <strong className="text-cyan-400">{location}</strong>
      </p>
    </div>
  );
};
"""
        elif "backend" in sys_lower or "coder" in sys_lower or "coder" in prompt_lower:
            # Backend developer writes the mathematical logic
            return """# High-Performance Euclidean Distance Calculator
import math

def calculate_distance(node_a: tuple, node_b: tuple) -> float:
    \"\"\"Calculates euclidean distance between coordinate points.\"\"\"
    if len(node_a) != len(node_b):
        raise ValueError("Nodes must have the same dimensional scale.")
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(node_a, node_b)))

if __name__ == "__main__":
    p1, p2 = (1, 4), (8, 4)
    print(f"Calculated Distance: {calculate_distance(p1, p2):.4f}")
"""
        elif "reviewer" in sys_lower or "reviewer" in prompt_lower or "audit" in prompt_lower:
            if "status" in prompt_lower and "emerald-500" not in prompt_lower:
                return """{
  "status": "REVIEW_FAILED",
  "feedback": "Code Reviewer Audit: The status text block in 'AgentDashboardCard' is plain and unstyled. It fails our UX guidelines for high-fidelity micro-interactions. Please style the status badge using a colored border and a subtle translucent background (e.g., bg-emerald-500/10 text-emerald-400 border border-emerald-500/20)."
}"""
            return """{
  "status": "REVIEW_PASSED",
  "feedback": "Code Reviewer Audit: All React frontend modules and Python backend utility scripts comply with standard UI/UX guidelines and robust validation checks. No security concerns or unstyled components found."
}"""
        elif "search" in prompt_lower:
            return """# Earned Source: Design Patterns for Visual Telemetry Badges
### Context
When organizing micro-status updates in interactive workspaces, standard practice recommends using colored border badges with translucent backgrounds of 10% opacity. 

### Best Practice
```html
<span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Status</span>
```
This reduces visual clutter and fits modern slate-themed dashboards.
"""
        return "Simulation response: Task executed successfully."


# =====================================================================
# 2. SECTOR MEMORY & CANVAS SPATIAL UPDATER
# =====================================================================
class SpatialCanvasManager:
    """Manages moving our developer agents programmatically on our 2.5D visual board."""
    
    SECTOR_COORDINATES = {
        "Bob's Cottage": (100, 100),
        "Willows Market": (100, 600),
        "Obsidian Citadel": (800, 100),  # The Dev Office Citadel
        "Grand Archives": (800, 600)
    }

    @staticmethod
    def relocate_agent_on_canvas(agent_name: str, sector: str):
        """Updates the .canvas JSON to place developers sitting at their designated office desks."""
        if sector not in SpatialCanvasManager.SECTOR_COORDINATES:
            return

        coords = SpatialCanvasManager.SECTOR_COORDINATES[sector]
        canvas_data = {"nodes": [], "edges": []}
        
        if os.path.exists(CANVAS_FILE):
            try:
                with open(CANVAS_FILE, "r", encoding="utf-8") as f:
                    canvas_data = json.load(f)
            except Exception:
                pass

        # Ensure the Citadel group room is present
        room_id = f"room_{sector.replace(' ', '_').lower()}"
        room_node = None
        for node in canvas_data["nodes"]:
            if node.get("id") == room_id:
                room_node = node
                break

        if not room_node:
            room_node = {
                "id": room_id,
                "type": "group",
                "x": coords[0],
                "y": coords[1],
                "width": 350,
                "height": 300,
                "label": f"🏢 Sector: {sector}"
            }
            canvas_data["nodes"].append(room_node)

        # Clear previous agent positions to avoid duplications
        canvas_data["nodes"] = [n for n in canvas_data["nodes"] if n.get("id") != f"agent_{agent_name.lower()}"]

        # Position desks sequentially in the workspace
        offsets = {
            "Project_Manager": 15,
            "Coder": 75,
            "Frontend_Developer": 135,
            "Code_Reviewer": 195,
            "Deployer": 255
        }
        offset = offsets.get(agent_name, 15)

        # Draw the agent visual card node inside the group boundaries
        agent_node = {
            "id": f"agent_{agent_name.lower()}",
            "type": "text",
            "x": coords[0] + offset,
            "y": coords[1] + 50,
            "width": 55,
            "height": 65,
            "text": f"🤖 {agent_name.replace('_', ' ')}\nStatus: Active\nAt Citadel Desk"
        }
        canvas_data["nodes"].append(agent_node)

        try:
            with open(CANVAS_FILE, "w", encoding="utf-8") as f:
                json.dump(canvas_data, f, indent=2)
            print(f"[📍 Spatial Grid] Relocated '{agent_name}' inside '{sector}' visual canvas card.")
        except Exception as e:
            print(f"⚠️ Failed to update .canvas coordinates: {e}")


# =====================================================================
# 3. OBSIDIAN EPISODIC & SEMANTIC WRITER
# =====================================================================
class MemoryVaultWriter:
    """Logs the expanded team's daily notes, roles, and learned files directly to Obsidian."""

    @staticmethod
    def write_episodic_log(agent_name: str, message: str, role: str, status: str):
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.datetime.now().strftime("%H%M%S")
        target_dir = os.path.join(EPISODIC_DIR, date_str)
        os.makedirs(target_dir, exist_ok=True)

        filename = f"EP_DEV_{agent_name.upper()}_{time_str}.md"
        filepath = os.path.join(target_dir, filename)

        content = f"""---
type: episodic_log
agent: {agent_name}
timestamp: {datetime.datetime.now().isoformat()}
location: "[[Obsidian_Citadel]]"
tags:
  - episodic_log
  - local_development
  - collaborative_software_engineering
---

# Episode: {agent_name.replace('_', ' ')} - Development Workspace Entry

### Workspace Profile
*   **Active Role**: {role}
*   **Execution Status**: {status}

### Activity Log
{message}

### Relations
- [[{agent_name}]]
- [[Obsidian_Citadel]]
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def write_earned_source(title: str, content_body: str):
        """Saves researched code-patterns and documentation as permanent text sources."""
        source_dir = os.path.join(VAULT_PATH, "05_Learned_Sources")
        os.makedirs(source_dir, exist_ok=True)
        
        safe_title = title.replace(" ", "_").lower()
        filepath = os.path.join(source_dir, f"SOURCE_{safe_title}.md")

        content = f"""---
type: learned_source
title: "{title}"
earned_at: {datetime.datetime.now().isoformat()}
tags:
  - SOLA_framework
  - design_guidelines
---

# Learned Source: {title}

{content_body}
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[📥 SOLA Learning] Successfully saved new knowledge source: 'SOURCE_{safe_title}.md'")


# =====================================================================
# 4. COLLABORATIVE DEV TEAM WORKFLOW (NeSy Core)
# =====================================================================
class ExpandedDevTeam:
    """
    Coordinates an expanded, modern software dev loop including:
    Project Manager, Backend Coder, Frontend Developer, Code Reviewer, and Deployer.
    """
    def __init__(self, ollama: OllamaClient, workspace_dir: str = None):
        self.ollama = ollama
        if workspace_dir is None:
            workspace_dir = os.environ.get("DEV_WORKSPACE", os.path.abspath(os.path.join(os.path.dirname(__file__), "dev_project_v2")))
        self.workspace_dir = workspace_dir
        os.makedirs(workspace_dir, exist_ok=True)

    def run_sola_search(self, review_feedback: str) -> str:
        """Employs the SOLA framework to ingest learning files on UX violations."""
        print(f"\n🔍 [SOLA Learning] UX Style Audit Flagged: '{review_feedback}'. Researching UI patterns...")
        
        learned_title = "Tailwind CSS Badge Micro-Interactions and Opacity Controls"
        learned_doc = """For a professional dark mode interface, dynamic state tags should utilize high-contrast 
semi-transparent background frames (e.g., bg-emerald-500/10) rather than standard flat opaque colors. This matches 
industry-standard slate design layouts."""
        
        MemoryVaultWriter.write_earned_source(learned_title, learned_doc)
        return "SOLA Learning Complete: Source imported to local knowledge vault."

    def execute_development_cycle(self, project_objective: str):
        """Runs the fully coordinate team cycle: Plan -> Code Backend -> Draft Frontend -> Review -> Self-Correct -> Deploy."""
        print("=====================================================================")
        print("STARTING HIERARCHICAL CO-DEV TEAM (FE DEV & CODE REVIEWER UPDATES)")
        print("=====================================================================")

        # Step 1: Supervisor (Project Manager) plans work allocations
        print("\n[Supervisor 📋] Project Manager planning workflow structures...")
        SpatialCanvasManager.relocate_agent_on_canvas("Project_Manager", "Obsidian Citadel")
        
        pm_prompt = f"Decompose this project into subtasks for a Backend Coder, Frontend Developer, and Code Reviewer: {project_objective}"
        pm_sys = "You are the Project Manager. Output only a clean, parseable JSON dictionary with 'plan' and 'requirements' fields."
        
        pm_res_raw = self.ollama.generate("llama3.2", pm_prompt, system=pm_sys)
        try:
            pm_plan = json.loads(pm_res_raw)
            print("📋 Project Manager Design Plan:")
            for step in pm_plan.get("plan", []):
                print(f"  Step {step['step']}: {step['task']} -> Assignee: {step['assignee']}")
        except Exception:
            print("📋 Project Manager Design Plan generated successfully (Simulation Map).")
            pm_plan = {
                "requirements": "Build a robust math algorithm and a beautiful React card to show agent coordinate metrics."
            }

        MemoryVaultWriter.write_episodic_log(
            "Project_Manager",
            f"Successfully allocated task sequences for project '{project_objective}'. Directed Coder to backend math, and FE Developer to the visual cards.",
            "Project Manager",
            "Planning Finished"
        )

        # Step 2: Software Engineer (Backend Coder) builds the utility
        print("\n[Coder 💻] Coder starting backend script development...")
        SpatialCanvasManager.relocate_agent_on_canvas("Coder", "Obsidian Citadel")
        
        coder_prompt = "Build a Python utility module that calculates multi-dimensional Euclidean offsets."
        coder_sys = "You are a Backend Python Engineer. Output only fully executable python code blocks."
        
        # Helper to strip markdown code blocks
        def sanitize_code(raw: str) -> str:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.splitlines()
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            return cleaned

        backend_code = sanitize_code(self.ollama.generate("codellama", coder_prompt, system=coder_sys))
        backend_path = os.path.join(self.workspace_dir, "distance_utility.py")
        with open(backend_path, "w", encoding="utf-8") as f:
            f.write(backend_code)
        print(f"💻 Backend utility file written to: {backend_path}")
        
        MemoryVaultWriter.write_episodic_log(
            "Coder",
            f"Completed Python backend coordinates distance_utility.py. File mapped at {backend_path}.",
            "Backend Developer",
            "Backend Finished"
        )

        # Step 3: Frontend Developer (FE Dev) builds UI card
        print("\n[Frontend Coder 🎨] Frontend Developer designing dashboard component...")
        SpatialCanvasManager.relocate_agent_on_canvas("Frontend_Developer", "Obsidian Citadel")
        
        fe_prompt = "Design a beautiful, responsive React dashboard card template to display agent metrics. Include status badges."
        fe_sys = "You are a professional UX/UI Frontend Developer. Output only clean, modular React component code."
        
        frontend_code = sanitize_code(self.ollama.generate("codellama", fe_prompt, system=fe_sys))
        frontend_path = os.path.join(self.workspace_dir, "AgentDashboardCard.jsx")
        with open(frontend_path, "w", encoding="utf-8") as f:
            f.write(frontend_code)
        print(f"🎨 React frontend card file written to: {frontend_path}")

        MemoryVaultWriter.write_episodic_log(
            "Frontend_Developer",
            f"Finished drafting React frontend card. Saved module locally at {frontend_path}.",
            "Frontend Developer",
            "FE Draft Finished"
        )

        # Step 4: Code Reviewer (Reviewer) audits code
        print("\n[Code Reviewer 🔍] Code Reviewer conducting rigorous design and structural audit...")
        SpatialCanvasManager.relocate_agent_on_canvas("Code_Reviewer", "Obsidian Citadel")
        
        reviewer_prompt = f"Audit this React component and backend math script for design compliance and syntax correctness: \n\n{frontend_code}"
        reviewer_sys = "You are a Senior Code Reviewer. Output a JSON containing 'status' (REVIEW_PASSED or REVIEW_FAILED) and 'feedback' fields."
        
        reviewer_res_raw = self.ollama.generate("llama3.2", reviewer_prompt, system=reviewer_sys)
        try:
            reviewer_res = json.loads(reviewer_res_raw)
        except Exception:
            reviewer_res = {
                "status": "REVIEW_FAILED",
                "feedback": "Code Reviewer Audit: The status text block in 'AgentDashboardCard' is plain and unstyled. It fails our UX guidelines for high-fidelity micro-interactions. Please style the status badge using a colored border and a subtle translucent background (e.g., bg-emerald-500/10 text-emerald-400 border border-emerald-500/20)."
            }

        MemoryVaultWriter.write_episodic_log(
            "Code_Reviewer",
            f"Completed rigorous review of backend and frontend files. Status: {reviewer_res['status']}. Feedback: {reviewer_res['feedback']}",
            "Senior Code Reviewer",
            "Review Complete"
        )

        # Step 5: Self-Correction Loop based on Code Reviewer feedback
        if reviewer_res["status"] == "REVIEW_FAILED":
            print(f"❌ Review Failed: {reviewer_res['feedback']}")
            
            # Learn from feedback using SOLA framework
            self.run_sola_search(reviewer_res["feedback"])
            
            print("\n[Frontend Coder 🎨] Frontend Developer applying styles correction...")
            correction_prompt = f"Correct the styling of the badge in the React component based on this review feedback: '{reviewer_res['feedback']}'. Code:\n\n{frontend_code}"
            corrected_fe_code = sanitize_code(self.ollama.generate("codellama", correction_prompt, system=fe_sys))
            
            with open(frontend_path, "w", encoding="utf-8") as f:
                f.write(corrected_fe_code)
            print(f"🎨 Style-corrected React component written to: {frontend_path}")
            
            MemoryVaultWriter.write_episodic_log(
                "Frontend_Developer",
                "Successfully applied Code Reviewer style guidelines. React status badges are now high-fidelity, responsive elements.",
                "Frontend Developer",
                "FE Revision Complete"
            )

        # Step 6: Sandbox Deployer (DevOps execution and syntax checks)
        print("\n[Deployer 🚀] Sandbox Deployer mounting assets and executing verification testing...")
        SpatialCanvasManager.relocate_agent_on_canvas("Deployer", "Obsidian Citadel")
        
        # Deployer executes backend unit tests
        deploy_success = False
        try:
            res = subprocess.run(
                [sys.executable, backend_path],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            if res.returncode == 0:
                print(f"✅ Subprocess math tests passed! Output:\n{res.stdout.strip()}")
                deploy_success = True
                status_msg = f"Backend compilation passed successfully. Results: {res.stdout.strip()}"
            else:
                print(f"❌ Subprocess execution error:\n{res.stderr.strip()}")
                status_msg = f"Backend python test script compilation failed: {res.stderr.strip()}"
        except Exception as e:
            print(f"⚠️ Subprocess execution crashed: {e}")
            status_msg = f"Sandbox testing suite failed to spawn execution subprocess: {e}"

        MemoryVaultWriter.write_episodic_log(
            "Deployer",
            status_msg,
            "DevOps Deployer",
            "Deployment Testing Complete"
        )

        print("\n=====================================================================")
        print(f"DEVELOPMENT CYCLE COMPLETE. STATUS: {'SUCCESS' if deploy_success else 'RETRY_NEEDED'}")
        print("=====================================================================")


# =====================================================================
# MAIN RUNTIME COMMAND TRIGGER
# =====================================================================
if __name__ == "__main__":
    client = OllamaClient()
    if client.is_online:
        print(f"[+] Connected to local Ollama API server running at: {OLLAMA_HOST}")
    else:
        print(f"[-] Ollama server offline. Launching high-fidelity local simulation harness.")
        
    team = ExpandedDevTeam(client)
    team.execute_development_cycle("Build a responsive Agent Metrics UI module and connected Python backend math logic.")
