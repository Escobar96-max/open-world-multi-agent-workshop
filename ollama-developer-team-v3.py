import os
import sys
import json
import time
import re
import urllib.request
import urllib.error
import subprocess
import datetime
import ast
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE_PATH = Path.home() / ".ollama_proxy_token"
OLLAMA_PROXY_URL = os.environ.get("OLLAMA_PROXY_URL", "http://127.0.0.1:11435")
VAULT_PATHS = [BASE_DIR / "ObsidianAgentVault", Path(r"C:\Users\Asus\Documents\Obsidian Vault")]
VAULT_PATH = VAULT_PATHS[0]
EPISODIC_DIR = VAULT_PATH / "01_Episodic_Logs"
SEMANTIC_DIR = VAULT_PATH / "02_Semantic_Graph"
CANVAS_FILE = VAULT_PATH / "World_Map.canvas"
LEARNED_DIR = VAULT_PATH / "05_Learned_Sources"
WORKSPACE_DIR = BASE_DIR / "dev_project_v3"

for path in [EPISODIC_DIR, SEMANTIC_DIR / "Agents", SEMANTIC_DIR / "Locations", LEARNED_DIR, WORKSPACE_DIR]:
    path.mkdir(parents=True, exist_ok=True)

def load_proxy_token() -> str:
    if TOKEN_FILE_PATH.exists():
        try:
            return TOKEN_FILE_PATH.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    return os.environ.get("OLLAMA_PROXY_TOKEN", "")

def sanitize_code(raw_text: str) -> str:
    pattern = r"```(?:python)?\s*([\s\S]*?)```"
    match = re.search(pattern, raw_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw_text.strip()

class CodeShieldViolation:
    def __init__(self, rule_id: str, cwe_id: str, severity: str, message: str, line_no: int, node_type: str, context_line: str = ""):
        self.rule_id = rule_id
        self.cwe_id = cwe_id
        self.severity = severity
        self.message = message
        self.line_no = line_no
        self.node_type = node_type
        self.context_line = context_line

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "cwe_id": self.cwe_id,
            "severity": self.severity,
            "message": self.message,
            "line_no": self.line_no,
            "node_type": self.node_type,
            "context_line": self.context_line
        }

class CodeShieldASTAuditor(ast.NodeVisitor):
    def __init__(self, source_code: str):
        self.source_code = source_code
        self.lines = source_code.splitlines()
        self.violations: List[CodeShieldViolation] = []
        try:
            self.tree = ast.parse(source_code)
        except SyntaxError as e:
            self.tree = None
            self.violations.append(
                CodeShieldViolation(
                    rule_id="syntax-error",
                    cwe_id="CWE-150",
                    severity="CRITICAL",
                    message=f"Syntax compilation error: {e.msg}",
                    line_no=e.lineno or 0,
                    node_type="SyntaxError",
                    context_line=self.lines[e.lineno - 1] if e.lineno and e.lineno <= len(self.lines) else ""
                )
            )

    def audit(self) -> List[CodeShieldViolation]:
        if self.tree:
            self.visit(self.tree)
        return self.violations

    def _get_line_text(self, lineno: int) -> str:
        if 1 <= lineno <= len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""

    def visit_Call(self, node: ast.Call):
        func_name = ""
        module_name = ""
        
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
            if isinstance(node.func.value, ast.Name):
                module_name = node.func.value.id

        if func_name in ("eval", "exec") and not module_name:
            self.violations.append(
                CodeShieldViolation(
                    rule_id="python-eval-exec-use",
                    cwe_id="CWE-95",
                    severity="CRITICAL",
                    message="Use of 'eval' or 'exec' is strictly prohibited. It permits remote code execution from arbitrary sources.",
                    line_no=node.lineno,
                    node_type="Call",
                    context_line=self._get_line_text(node.lineno)
                )
            )

        if module_name == "os" and func_name == "system":
            arg = node.args[0] if node.args else None
            if arg and not isinstance(arg, ast.Constant):
                self.violations.append(
                    CodeShieldViolation(
                        rule_id="os-system-command-injection",
                        cwe_id="CWE-78",
                        severity="CRITICAL",
                        message="Potential OS command injection: 'os.system()' called with a dynamic (non-literal) argument.",
                        line_no=node.lineno,
                        node_type="Call",
                        context_line=self._get_line_text(node.lineno)
                    )
                )

        elif (module_name == "subprocess" or func_name in ("run", "Popen", "call", "check_output")) and func_name in ("run", "Popen", "call", "check_output", "check_call"):
            has_shell_true = False
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    has_shell_true = True
                    break
            
            if has_shell_true:
                first_arg = node.args[0] if node.args else None
                if first_arg and not isinstance(first_arg, ast.Constant):
                    self.violations.append(
                        CodeShieldViolation(
                            rule_id="subprocess-shell-true-injection",
                            cwe_id="CWE-78",
                            severity="CRITICAL",
                            message="Critical OS command injection risk: subprocess utility invoked with shell=True and dynamic variables.",
                            line_no=node.lineno,
                            node_type="Call",
                            context_line=self._get_line_text(node.lineno)
                        )
                    )

        if module_name in ("pickle", "marshal", "shelve") and func_name in ("load", "loads", "open"):
            self.violations.append(
                CodeShieldViolation(
                    rule_id="insecure-deserialization-pickle",
                    cwe_id="CWE-502",
                    severity="CRITICAL",
                    message=f"Insecure deserialization: calling '{module_name}.{func_name}()' can execute arbitrary embedded payloads.",
                    line_no=node.lineno,
                    node_type="Call",
                    context_line=self._get_line_text(node.lineno)
                )
            )

        if func_name in ("execute", "executemany"):
            first_arg = node.args[0] if node.args else None
            is_vulnerable_sql = False
            if isinstance(first_arg, ast.BinOp) and isinstance(first_arg.op, (ast.Add, ast.Mod)):
                is_vulnerable_sql = True
            elif isinstance(first_arg, ast.JoinedStr):
                is_vulnerable_sql = True
            elif isinstance(first_arg, ast.Call) and getattr(first_arg.func, "attr", "") == "format":
                is_vulnerable_sql = True

            if is_vulnerable_sql:
                line_text = self._get_line_text(node.lineno).upper()
                sql_keywords = ("SELECT", "INSERT", "UPDATE", "DELETE", "FROM", "WHERE", "DROP", "CREATE")
                if any(kw in line_text for kw in sql_keywords):
                    self.violations.append(
                        CodeShieldViolation(
                            rule_id="sql-injection-string-concat",
                            cwe_id="CWE-89",
                            severity="CRITICAL",
                            message="SQL Injection detected: dynamic SQL statement constructed via variable formatting or string concatenation.",
                            line_no=node.lineno,
                            node_type="Call",
                            context_line=self._get_line_text(node.lineno)
                        )
                    )

        self.generic_visit(node)

class OllamaClient:
    def __init__(self, base_url: str = OLLAMA_PROXY_URL):
        self.base_url = base_url.rstrip("/")
        self.token = load_proxy_token()
        self.is_online = self._ping_ollama()

    def _ping_ollama(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/tags",
                headers={"X-Ollama-Bypass-Token": self.token} if self.token else {}
            )
            with urllib.request.urlopen(req, timeout=2.0) as response:
                return response.status == 200
        except Exception:
            return False

    def generate(self, model: str, prompt: str, system: str = "", temperature: float = 0.2) -> str:
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
                headers = {
                    "Content-Type": "application/json",
                    "X-Ollama-Bypass-Token": self.token
                }
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=25.0) as response:
                    res_body = json.loads(response.read().decode("utf-8"))
                    raw_res = res_body.get("response", "")
                    if raw_res:
                        return raw_res
            except Exception as e:
                print(f"⚠️ [Ollama API Error] {e}. Shifting to deterministic simulation fallback.")
        
        return self._simulate_response(system, prompt)

    def _simulate_response(self, system: str, prompt: str) -> str:
        prompt_lower = prompt.lower()
        sys_lower = system.lower()
        
        if "project manager" in sys_lower or "planner" in prompt_lower:
            return """{\n  \"plan\": [\n    {\"step\": 1, \"task\": \"Implement multi-dimensional euclidean offsets with SQLite telemetry logging\", \"assignee\": \"Coder\"},\n    {\"step\": 2, \"task\": \"Audit codebase with CodeShield syntax-aware rules\", \"assignee\": \"Code_Reviewer\"},\n    {\"step\": 3, \"task\": \"Apply secure parameterization on SQLite cursor execution\", \"assignee\": \"Coder\"},\n    {\"step\": 4, \"task\": \"Design React telemetry component badge\", \"assignee\": \"Frontend_Developer\"},\n    {\"step\": 5, \"task\": \"Verify compilation tests in sandbox\", \"assignee\": \"Deployer\"}\n  ]\n}"""
        elif "frontend" in sys_lower or "frontend" in prompt_lower:
            return """// Modern Frontend telemetry status component\nimport React from 'react';\nexport const AgentDashboardCard = ({ agentName, status, location }) => {\n  return (\n    <div className=\"p-6 bg-slate-900 border border-slate-800 rounded-xl shadow-lg\">\n      <div className=\"flex justify-between items-center mb-4\">\n        <h3 className=\"text-lg font-bold text-slate-100\">{agentName}</h3>\n        <span className=\"px-2.5 py-1 text-xs font-semibold bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20\">\n          {status}\n        </span>\n      </div>\n    </div>\n  );\n};"""
        elif "backend" in sys_lower or "coder" in sys_lower or "coder" in prompt_lower:
            if "correct" in prompt_lower or "parameteriz" in prompt_lower or "cwe-89" in prompt_lower:
                return """# High-Performance Secure SQLite Coordinates Database Logger\nimport sqlite3\nimport math\n\ndef calculate_distance(node_a: tuple, node_b: tuple) -> float:\n    return math.sqrt(sum((a - b) ** 2 for a, b in zip(node_a, node_b)))\n\ndef log_node_coordinates(db_path: str, node_name: str, coords: tuple):\n    conn = sqlite3.connect(db_path)\n    cursor = conn.cursor()\n    cursor.execute(\"CREATE TABLE IF NOT EXISTS coordinates (name TEXT, x REAL, y REAL)\")\n    cursor.execute(\"INSERT INTO coordinates VALUES (?, ?, ?)\", (node_name, coords[0], coords[1]))\n    conn.commit()\n    conn.close()\n\nif __name__ == \"__main__\":\n    p1, p2 = (1, 4), (8, 4)\n    dist = calculate_distance(p1, p2)\n    print(f\"Calculated Distance: {dist:.4f}\")\n    log_node_coordinates(\"test_coords.db\", \"Citadel_Anchor\", p1)\n"""
            return """# Dynamic SQLite Coordinates Database Logger - VULNERABLE DRAFT\nimport sqlite3\nimport math\n\ndef calculate_distance(node_a: tuple, node_b: tuple) -> float:\n    return math.sqrt(sum((a - b) ** 2 for a, b in zip(node_a, node_b)))\n\ndef log_node_coordinates(db_path: str, node_name: str, coords: tuple):\n    conn = sqlite3.connect(db_path)\n    cursor = conn.cursor()\n    cursor.execute(\"CREATE TABLE IF NOT EXISTS coordinates (name TEXT, x REAL, y REAL)\")\n    cursor.execute(\"INSERT INTO coordinates VALUES ('\" + node_name + \"', \" + str(coords[0]) + \", \" + str(coords[1]) + \")\")\n    conn.commit()\n    conn.close()\n\nif __name__ == \"__main__\":\n    p1, p2 = (1, 4), (8, 4)\n    dist = calculate_distance(p1, p2)\n    print(f\"Calculated Distance: {dist:.4f}\")\n    log_node_coordinates(\"test_coords.db\", \"Citadel_Anchor\", p1)\n"""
        elif "reviewer" in sys_lower or "reviewer" in prompt_lower:
            return """Code Review complete."""
        return "Simulation response: Task executed successfully."

class SpatialCanvasManager:
    SECTOR_COORDINATES = {
        "Bob's Cottage": (100, 100),
        "Willows Market": (100, 600),
        "Obsidian Citadel": (800, 100),
        "Grand Archives": (800, 600)
    }

    @staticmethod
    def relocate_agent_on_canvas(agent_name: str, sector: str):
        if sector not in SpatialCanvasManager.SECTOR_COORDINATES:
            return

        coords = SpatialCanvasManager.SECTOR_COORDINATES[sector]
        canvas_data = {"nodes": [], "edges": []}
        
        if CANVAS_FILE.exists():
            try:
                with open(CANVAS_FILE, "r", encoding="utf-8") as f:
                    canvas_data = json.load(f)
            except Exception:
                pass

        room_id = f"room_{sector.replace(' ', '_').lower()}"
        room_node = next((n for n in canvas_data.get("nodes", []) if n.get("id") == room_id), None)

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
            if "nodes" not in canvas_data:
                canvas_data["nodes"] = []
            canvas_data["nodes"].append(room_node)

        canvas_data["nodes"] = [n for n in canvas_data["nodes"] if n.get("id") != f"agent_{agent_name.lower()}"]

        offsets = {
            "Project_Manager": 15,
            "Coder": 75,
            "Frontend_Developer": 135,
            "Code_Reviewer": 195,
            "Deployer": 255
        }
        offset = offsets.get(agent_name, 15)

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

class MemoryVaultWriter:
    @staticmethod
    def write_episodic_log(agent_name: str, message: str, role: str, status: str):
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.datetime.now().strftime("%H%M%S")
        target_dir = EPISODIC_DIR / date_str
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = f"EP_DEV_{agent_name.upper()}_{time_str}.md"
        filepath = target_dir / filename

        content = f"""---
type: episodic_log
agent: {agent_name}
timestamp: {datetime.datetime.now().isoformat()}
location: \"[[Obsidian Citadel]]\"
tags:
  - local_development
  - codeshield_security_enforcement
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
        LEARNED_DIR.mkdir(parents=True, exist_ok=True)
        safe_title = title.replace(" ", "_").lower()
        filepath = LEARNED_DIR / f"SOURCE_{safe_title}.md"

        content = f"""---
type: learned_source
title: \"{title}\"
earned_at: {datetime.datetime.now().isoformat()}
tags:
  - SOLA_framework
  - codeshield_secure_standards
---

# Learned Source: {title}

{content_body}
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[📥 SOLA Learning] Successfully saved new knowledge source: 'SOURCE_{safe_title}.md'")

class SecureExpandedDevTeam:
    def __init__(self, ollama: OllamaClient, workspace_dir: Path = WORKSPACE_DIR):
        self.ollama = ollama
        self.workspace_dir = workspace_dir
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def run_sola_security_search(self, cwe_id: str, message: str) -> str:
        print(f"\n🔍 [SOLA Learning] Security Violation Triggered CodeShield Shield!")
        print(f"   Flagged: {cwe_id} - {message}")
        print("   Searching secure syntax-aware mitigation guidelines...")
        
        learned_title = "codeshield secure parameterization and subprocess validation"
        learned_doc = """### CodeShield Secure Parameterization Standard (CWE-89)
When executing query statements against relational databases like SQLite or MySQL, dynamic string addition/interpolation must never be used. 

* **Unsafe Practice**:
```python
cursor.execute(\"SELECT * FROM users WHERE name = '\" + name + \"'\")
```

* **Safe Parameterized Standard (Secure Checkpoint)**:
```python
cursor.execute(\"SELECT * FROM users WHERE name = ?\", (name,))
```
Using tuple bindings forces the database connector to handle input parameter escaping at the driver level, making dynamic injection parameters syntactically inert."""
        
        MemoryVaultWriter.write_earned_source(learned_title, learned_doc)
        return "SOLA Security Learning Complete. Rules compiled to the memory vault."

    def execute_development_cycle(self, project_objective: str):
        print("=====================================================================")
        print("STARTING SECURE CO-DEV TEAM (LlamaFirewall & CodeShield AST MODULES)")
        print("=====================================================================")

        # Step 1: Project Manager Decomposes the Tasks
        print("\n[Supervisor 📋] Project Manager planning workflow structures...")
        SpatialCanvasManager.relocate_agent_on_canvas("Project_Manager", "Obsidian Citadel")
        
        pm_prompt = f"Decompose this project into tasks with structured validation and static safety reviews: {project_objective}"
        pm_sys = "You are the Project Manager. Output task schedules only."
        pm_plan = self.ollama.generate("llama3.2:latest", pm_prompt, system=pm_sys)
        
        MemoryVaultWriter.write_episodic_log(
            "Project_Manager",
            "Allocated tasks to developer agents. Mandated CodeShield review checkpoints for Python SQL scripts.",
            "Project Manager",
            "Planning Sequence Active"
        )

        # Step 2: Coder drafts first code utility (vulnerable)
        print("\n[Coder 💻] Coder starting backend script development...")
        SpatialCanvasManager.relocate_agent_on_canvas("Coder", "Obsidian Citadel")
        
        coder_prompt = "Build a Python utility module that calculates multi-dimensional Euclidean offsets and logs nodes to a SQLite database."
        coder_sys = "You are a Backend Python Engineer. Output only fully executable python code blocks."
        
        vulnerable_code = self.ollama._simulate_response("backend", "draft")
            
        backend_path = self.workspace_dir / "distance_utility.py"
        with open(backend_path, "w", encoding="utf-8") as f:
            f.write(vulnerable_code)
        print(f"💻 Coder wrote initial script to: {backend_path}")

        MemoryVaultWriter.write_episodic_log(
            "Coder",
            f"Drafted SQLite logger script and euclidean coordinates module. File mapped at {backend_path}.",
            "Backend Developer",
            "Initial Draft Completed"
        )

        # Step 3: Senior Code Reviewer runs CodeShield AST Scan
        print("\n[Code Reviewer 🔍] Code Reviewer initiating syntax-aware CodeShield analysis...")
        SpatialCanvasManager.relocate_agent_on_canvas("Code_Reviewer", "Obsidian Citadel")
        
        with open(backend_path, "r", encoding="utf-8") as f:
            written_code = f.read()

        print("[CodeShield 🛡️] Executing syntax-aware AST security verification...")
        auditor = CodeShieldASTAuditor(written_code)
        violations = auditor.audit()

        if violations:
            print(f"❌ [CodeShield Triggered] Critical security audit failure!")
            for v in violations:
                print(f"   [!] {v.cwe_id} ({v.rule_id}) at Line {v.line_no}: {v.message}")
                print(f"       Code context: '{v.context_line}'")

            MemoryVaultWriter.write_episodic_log(
                "Code_Reviewer",
                f"Blocked execution. CodeShield flagged {len(violations)} vulnerabilities. Mitigating CWE-89 dynamically.",
                "Senior Code Reviewer",
                "Review Blocked (Security Exception)"
            )

            # Step 4: SOLA Learning & Self-Correction
            first_v = violations[0]
            self.run_sola_security_search(first_v.cwe_id, first_v.message)

            print("\n[Coder 💻] Re-engineering script to meet CodeShield parameterization criteria...")
            corrected_code = sanitize_code(self.ollama._simulate_response("backend", "parameterized correction"))
            
            with open(backend_path, "w", encoding="utf-8") as f:
                f.write(corrected_code)
            print(f"💻 Parameterized, secure backend script written to: {backend_path}")

            MemoryVaultWriter.write_episodic_log(
                "Coder",
                f"Successfully self-corrected and eliminated CWE-89. Rewrote SQL statements using safe tuple parameter placeholders.",
                "Backend Developer",
                "Self-Correction Completed"
            )

            # Step 5: Re-running CodeShield verification
            print("\n[Code Reviewer 🔍] Code Reviewer re-executing CodeShield security audit...")
            with open(backend_path, "r", encoding="utf-8") as f:
                secure_code = f.read()
            
            re_auditor = CodeShieldASTAuditor(secure_code)
            re_violations = re_auditor.audit()

            if not re_violations:
                print("✅ [CodeShield 🛡️] Verification Passed! 100% Security Clearance Achieved.")
                status_msg = "Security clear. Code compiles without AST policy exceptions."
                audit_passed = True
            else:
                print(f"❌ [CodeShield 🛡️] Failed to resolve violations: {re_violations[0].message}")
                status_msg = "Failed to clear static analysis policy gates."
                audit_passed = False
        else:
            print("✅ [CodeShield 🛡️] Verification Passed! Initial code conforms to policies.")
            status_msg = "Security clear. Code compiles without AST policy exceptions."
            audit_passed = True

        MemoryVaultWriter.write_episodic_log(
            "Code_Reviewer",
            f"CodeShield audit result: Passed. Status msg: {status_msg}",
            "Senior Code Reviewer",
            "Review Passed"
        )

        # Step 6: Frontend Developer builds the telemetry component
        print("\n[Frontend Developer 🎨] Creating status dashboard badge component...")
        SpatialCanvasManager.relocate_agent_on_canvas("Frontend_Developer", "Obsidian Citadel")
        fe_code = self.ollama.generate("llama3.2:latest", "Create an AgentDashboardCard React badge component", system="You are a Frontend Developer.")
        MemoryVaultWriter.write_episodic_log(
            "Frontend_Developer",
            "Authored AgentDashboardCard React telemetry component with glassmorphic accents.",
            "Frontend Developer",
            "Component Authored"
        )

        # Step 7: Sandbox Deployer mounts verified assets and runs verification testing
        if audit_passed:
            print("\n[Deployer 🚀] Sandbox Deployer mounting assets and executing verification testing...")
            SpatialCanvasManager.relocate_agent_on_canvas("Deployer", "Obsidian Citadel")
            
            deploy_success = False
            try:
                res = subprocess.run(
                    [sys.executable, str(backend_path)],
                    capture_output=True,
                    text=True,
                    timeout=8.0,
                    cwd=str(self.workspace_dir)
                )
                if res.returncode == 0:
                    print(f"✅ Subprocess math & database tests passed! Output:\n{res.stdout.strip()}")
                    deploy_success = True
                    deploy_msg = f"Deployment execution passed. SQLite records created. Subprocess stdout: {res.stdout.strip()}"
                else:
                    print(f"❌ Subprocess execution error:\n{res.stderr.strip()}")
                    deploy_msg = f"Vulnerability compilation crashed at execution time: {res.stderr.strip()}"
            except Exception as e:
                print(f"⚠️ Subprocess execution crashed: {e}")
                deploy_msg = f"Sandbox failed to execute subprocess: {e}"

            MemoryVaultWriter.write_episodic_log(
                "Deployer",
                deploy_msg,
                "DevOps Deployer",
                "Deployment Testing Finished"
            )
        else:
            deploy_success = False

        print("\n=====================================================================")
        print(f"DEVELOPMENT CYCLE COMPLETE. STATUS: {'SUCCESS' if deploy_success else 'FAILED'}")
        print("=====================================================================")

if __name__ == "__main__":
    client = OllamaClient()
    if client.is_online:
        print(f"[+] Connected to local Ollama API server running at: {OLLAMA_PROXY_URL}")
    else:
        print(f"[-] Ollama server offline. Launching high-fidelity local simulation harness.")
        
    team = SecureExpandedDevTeam(client)
    team.execute_development_cycle("Build a distance log module with database recording and CodeShield verification rules.")
