import os
import sys
import ast
import time
import secrets
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from services.vault_manager import VaultManager, VaultSecurityError

logger = logging.getLogger("SoupClient")

# Disallowed AST nodes / function calls for sandbox security
FORBIDDEN_CALLS = {
    "system", "popen", "spawn", "fork", "execv", "execve",
    "remove", "unlink", "rmdir", "shutil", "subprocess"
}
FORBIDDEN_MODULES = {"subprocess", "os", "sys", "shutil", "pty", "socket"}

# Default RLVR Curriculum Modules
CURRICULUM_MODULES: Dict[str, Dict[str, Any]] = {
    "fibonacci_recursion": {
        "id": "fibonacci_recursion",
        "title": "Recursive & Dynamic Fibonacci",
        "category": "algorithms",
        "difficulty": 1,
        "xp_reward": 50,
        "description": "Implement `def fib(n: int) -> int:` that returns the n-th Fibonacci number. fib(0)=0, fib(1)=1.",
        "starter_code": "def fib(n: int) -> int:\n    # Return n-th Fibonacci number\n    pass\n",
        "test_cases": [
            {"input": (0,), "expected": 0},
            {"input": (1,), "expected": 1},
            {"input": (2,), "expected": 1},
            {"input": (7,), "expected": 13},
            {"input": (10,), "expected": 55},
        ],
        "entry_function": "fib"
    },
    "spatial_manhattan_distance": {
        "id": "spatial_manhattan_distance",
        "title": "Antigravity Spatial Manhattan Metric",
        "category": "spatial_physics",
        "difficulty": 1,
        "xp_reward": 60,
        "description": "Implement `def manhattan_distance(p1: tuple, p2: tuple) -> float:` returning |x1-x2| + |y1-y2|.",
        "starter_code": "def manhattan_distance(p1: tuple, p2: tuple) -> float:\n    # Calculate Manhattan distance\n    pass\n",
        "test_cases": [
            {"input": ((0, 0), (10, 10)), "expected": 20.0},
            {"input": ((15, 25), (20, 30)), "expected": 10.0},
            {"input": ((50, 50), (50, 50)), "expected": 0.0},
            {"input": ((0, 50), (50, 0)), "expected": 100.0},
        ],
        "entry_function": "manhattan_distance"
    },
    "token_escrow_validator": {
        "id": "token_escrow_validator",
        "title": "Double-Entry Escrow Verification",
        "category": "economy",
        "difficulty": 2,
        "xp_reward": 100,
        "description": "Implement `def validate_transaction(sender_balance: float, amount: float, fee: float) -> tuple:` returning `(is_valid: bool, remaining_balance: float)`. Must be invalid if amount <= 0, fee < 0, or total cost > sender_balance.",
        "starter_code": "def validate_transaction(sender_balance: float, amount: float, fee: float) -> tuple:\n    # Return (is_valid, remaining_balance)\n    pass\n",
        "test_cases": [
            {"input": (100.0, 50.0, 2.0), "expected": (True, 48.0)},
            {"input": (50.0, 50.0, 1.0), "expected": (False, 50.0)},
            {"input": (100.0, 0.0, 1.0), "expected": (False, 100.0)},
            {"input": (100.0, -10.0, 1.0), "expected": (False, 100.0)},
            {"input": (200.0, 150.0, 0.0), "expected": (True, 50.0)},
        ],
        "entry_function": "validate_transaction"
    },
    "vector_cosine_similarity": {
        "id": "vector_cosine_similarity",
        "title": "Semantic Vector Cosine Metric",
        "category": "memory",
        "difficulty": 2,
        "xp_reward": 120,
        "description": "Implement `def cosine_similarity(v1: list, v2: list) -> float:` returning dot(v1,v2)/(||v1||*||v2||). Returns 0.0 if any norm is zero.",
        "starter_code": "import math\n\ndef cosine_similarity(v1: list, v2: list) -> float:\n    # Compute cosine similarity\n    pass\n",
        "test_cases": [
            {"input": ([1.0, 0.0], [1.0, 0.0]), "expected": 1.0},
            {"input": ([1.0, 0.0], [0.0, 1.0]), "expected": 0.0},
            {"input": ([1.0, 1.0], [2.0, 2.0]), "expected": 1.0},
            {"input": ([0.0, 0.0], [1.0, 1.0]), "expected": 0.0},
        ],
        "entry_function": "cosine_similarity"
    }
}

class SoupClient:
    def __init__(
        self,
        vault_manager: Optional[VaultManager] = None,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None
    ):
        self.vault_manager = vault_manager or VaultManager()
        self.api_key = api_key or os.getenv("SOUP_ZERO_API_KEY", "")
        self.endpoint = endpoint or os.getenv("SOUP_ZERO_ENDPOINT", "https://trysoup.dev/zero/v1")
        self.modules = CURRICULUM_MODULES

    def get_modules(self) -> List[Dict[str, Any]]:
        """Returns metadata for all available training modules."""
        results = []
        for mod in self.modules.values():
            results.append({
                "id": mod["id"],
                "title": mod["title"],
                "category": mod["category"],
                "difficulty": mod["difficulty"],
                "xp_reward": mod["xp_reward"],
                "description": mod["description"],
                "starter_code": mod["starter_code"],
                "entry_function": mod["entry_function"]
            })
        return results

    def get_module(self, module_id: str) -> Optional[Dict[str, Any]]:
        return self.modules.get(module_id)

    def _security_check_ast(self, code_str: str) -> Tuple[bool, Optional[str]]:
        """Static AST inspection preventing malicious system calls or imports."""
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            return False, f"Syntax Error in submitted code: {e}"

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in FORBIDDEN_MODULES:
                        return False, f"Prohibited module import: '{alias.name}'"
            elif isinstance(node, ast.ImportFrom):
                if node.module in FORBIDDEN_MODULES:
                    return False, f"Prohibited from-import module: '{node.module}'"
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "__import__"}:
                    return False, f"Prohibited function execution: '{node.func.id}'"
                elif isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_CALLS:
                    return False, f"Prohibited attribute call: '{node.func.attr}'"

        return True, None

    def evaluate_code(self, module_id: str, code_str: str) -> Dict[str, Any]:
        """
        Executes submitted code against module test cases inside a safe local environment.
        Produces RLVR metrics: pass_rate, reward [0.0, 1.0], diagnostics.
        """
        module = self.modules.get(module_id)
        if not module:
            return {
                "success": False,
                "error": f"Module '{module_id}' not found.",
                "reward": 0.0,
                "tests_passed": 0,
                "total_tests": 0,
                "diagnostics": ["Unknown curriculum module."]
            }

        safe, err = self._security_check_ast(code_str)
        if not safe:
            return {
                "success": False,
                "error": err,
                "reward": 0.0,
                "tests_passed": 0,
                "total_tests": len(module["test_cases"]),
                "diagnostics": [f"Security AST verification rejected code: {err}"]
            }

        # Safe local execution namespace
        import math
        exec_scope = {
            "math": math,
            "__builtins__": {
                "abs": abs,
                "len": len,
                "range": range,
                "min": min,
                "max": max,
                "sum": sum,
                "tuple": tuple,
                "list": list,
                "dict": dict,
                "int": int,
                "float": float,
                "bool": bool,
                "str": str,
                "round": round,
                "enumerate": enumerate,
                "zip": zip,
                "True": True,
                "False": False,
                "None": None
            }
        }

        try:
            exec(code_str, exec_scope)
        except Exception as e:
            return {
                "success": False,
                "error": f"Runtime error compiling code: {type(e).__name__}: {str(e)}",
                "reward": 0.0,
                "tests_passed": 0,
                "total_tests": len(module["test_cases"]),
                "diagnostics": [f"Runtime error during script execution: {str(e)}"]
            }

        entry_fn_name = module["entry_function"]
        entry_fn = exec_scope.get(entry_fn_name)
        if not entry_fn or not callable(entry_fn):
            return {
                "success": False,
                "error": f"Entry point function '{entry_fn_name}' was not defined.",
                "reward": 0.0,
                "tests_passed": 0,
                "total_tests": len(module["test_cases"]),
                "diagnostics": [f"Missing required function '{entry_fn_name}'."]
            }

        # Run test cases
        test_cases = module["test_cases"]
        passed = 0
        diagnostics = []

        for idx, tc in enumerate(test_cases):
            inputs = tc["input"]
            expected = tc["expected"]
            try:
                actual = entry_fn(*inputs)
                # Tolerance for float comparison
                if isinstance(expected, float) and isinstance(actual, (int, float)):
                    match = abs(actual - expected) < 1e-5
                else:
                    match = (actual == expected)

                if match:
                    passed += 1
                    diagnostics.append(f"Test #{idx+1}: PASS (args={inputs} -> {actual})")
                else:
                    diagnostics.append(f"Test #{idx+1}: FAIL (args={inputs}, expected {expected}, got {actual})")
            except Exception as e:
                diagnostics.append(f"Test #{idx+1}: ERROR ({type(e).__name__}: {str(e)})")

        total = len(test_cases)
        pass_rate = passed / total if total > 0 else 0.0
        reward = round(pass_rate, 4)
        success = (pass_rate >= 0.8)

        return {
            "success": success,
            "reward": reward,
            "tests_passed": passed,
            "total_tests": total,
            "pass_rate": pass_rate,
            "diagnostics": diagnostics
        }

    def process_solution_submission(
        self,
        agent_id: str,
        module_id: str,
        code_str: str
    ) -> Dict[str, Any]:
        """
        Evaluates solution, and if passing (reward >= 0.8), grants XP, updates profile,
        records graduation memory, and updates world leaderboard.
        """
        self.vault_manager.validate_identifier(agent_id)
        evaluation = self.evaluate_code(module_id, code_str)
        module = self.modules.get(module_id)

        if not evaluation["success"]:
            return {
                "status": "REJECTED",
                "agent_id": agent_id,
                "module_id": module_id,
                "evaluation": evaluation,
                "graduated": False
            }

        # Success - Award XP and record graduation
        xp_awarded = module["xp_reward"]
        now_iso = datetime.now(timezone.utc).isoformat()
        grad_id = f"grad_{int(time.time())}_{secrets.token_hex(2)}"

        # 1. Update Agent Profile
        profile_updated = False
        new_level = 1
        new_xp = xp_awarded
        try:
            fm, body = self.vault_manager.get_agent_profile(agent_id)
            current_xp = fm.get("xp", 0) + xp_awarded
            current_level = fm.get("level", 1)
            # Level up every 100 XP
            new_level = max(current_level, (current_xp // 100) + 1)
            badges = fm.get("badges", [])
            badge_name = f"sanctum_{module_id}"
            if badge_name not in badges:
                badges.append(badge_name)

            fm["xp"] = current_xp
            fm["level"] = new_level
            fm["badges"] = badges
            fm["last_active"] = now_iso
            self.vault_manager.write_agent_profile(agent_id, fm, body)
            profile_updated = True
            new_xp = current_xp
        except Exception as e:
            logger.warning(f"Could not update profile for {agent_id}: {e}")

        # 2. Add Graduation Memory
        memory_content = (
            f"🎓 Synthesis Sanctum RLVR Graduation: Completed module '{module['title']}' "
            f"with verified reward {evaluation['reward']} (Pass rate: {evaluation['pass_rate']*100:.1f}%). "
            f"Awarded +{xp_awarded} XP."
        )
        try:
            self.vault_manager.add_agent_memory(
                agent_id=agent_id,
                memory_id=grad_id,
                content=memory_content,
                importance=9,
                source="SynthesisSanctum_RLVR",
                tags=["synthesis_sanctum", "rlvr_graduation", module_id, "badge_earned"]
            )
        except Exception as e:
            logger.warning(f"Could not log graduation memory for {agent_id}: {e}")

        # 3. Update World Leaderboard
        self.update_leaderboard(agent_id, module_id, evaluation["reward"], new_xp, new_level)

        return {
            "status": "GRADUATED",
            "agent_id": agent_id,
            "module_id": module_id,
            "module_title": module["title"],
            "evaluation": evaluation,
            "xp_awarded": xp_awarded,
            "total_xp": new_xp,
            "level": new_level,
            "badge_earned": f"sanctum_{module_id}",
            "graduated": True
        }

    def update_leaderboard(
        self,
        agent_id: str,
        module_id: str,
        score: float,
        xp: int,
        level: int
    ) -> None:
        """Appends/updates agent in /vault/World/leaderboard.md."""
        leaderboard_path = self.vault_manager.world_path / "leaderboard.md"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        board_data: Dict[str, Dict[str, Any]] = {}

        if leaderboard_path.is_file():
            try:
                fm, body = self.vault_manager.read_file(leaderboard_path)
                entries = fm.get("standings", [])
                for entry in entries:
                    board_data[entry["agent_id"]] = entry
            except Exception:
                pass

        current = board_data.get(agent_id, {
            "agent_id": agent_id,
            "xp": 0,
            "level": 1,
            "completed_modules": [],
            "last_updated": now_iso
        })

        current["xp"] = xp
        current["level"] = level
        current["last_updated"] = now_iso
        if module_id not in current.get("completed_modules", []):
            mods = current.get("completed_modules", [])
            mods.append(module_id)
            current["completed_modules"] = mods

        board_data[agent_id] = current

        # Sort standings by XP descending
        sorted_standings = sorted(board_data.values(), key=lambda x: x.get("xp", 0), reverse=True)

        body_lines = [
            "# 🏆 Synthesis Sanctum: Global Agent Leaderboard",
            "",
            f"*Last Synchronized: {now_iso}*",
            "",
            "| Rank | Agent | Level | XP | Modules Completed | Last Active |",
            "| :--- | :--- | :---: | :---: | :--- | :--- |"
        ]

        for rank, item in enumerate(sorted_standings, 1):
            mods_str = ", ".join(item.get("completed_modules", [])) or "None"
            body_lines.append(
                f"| #{rank} | **[[{item['agent_id']}]]** | {item.get('level', 1)} | {item.get('xp', 0)} | {mods_str} | {item.get('last_updated', '')} |"
            )

        new_fm = {
            "title": "Synthesis Sanctum Global Leaderboard",
            "updated_at": now_iso,
            "total_agents": len(sorted_standings),
            "standings": sorted_standings
        }

        self.vault_manager.write_file(leaderboard_path, new_fm, "\n".join(body_lines))

    def get_leaderboard(self) -> Dict[str, Any]:
        """Returns structured leaderboard standings from vault."""
        leaderboard_path = self.vault_manager.world_path / "leaderboard.md"
        if not leaderboard_path.is_file():
            return {"title": "Leaderboard", "total_agents": 0, "standings": []}
        try:
            fm, _ = self.vault_manager.read_file(leaderboard_path)
            return fm
        except Exception:
            return {"title": "Leaderboard", "total_agents": 0, "standings": []}
