import os
import re
import sys
import time
import shutil
import logging
import subprocess
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

from services.vault_manager import VaultManager

logger = logging.getLogger("DevLoopEngine")

# Safety rules: Allowed and forbidden paths for auto-patching
ALLOWED_PATCH_DIRS = {"services", "api", "tests"}
BLOCKED_FILES = {"gatekeeper.py", ".env", ".env.example", ".env.local"}

class DevLoopSafetyError(Exception):
    pass

class DevLoopEngine:
    """
    Architect_Prime Self-Healing Dev Loop Engine.
    Executes automated test suites, diagnoses tracebacks and test failures,
    generates targeted patch candidates with rollback protection,
    and logs self-healing milestones into the Obsidian knowledge vault.
    """
    def __init__(
        self,
        vault_manager: Optional[VaultManager] = None,
        project_root: Optional[str] = None
    ):
        self.vault_manager = vault_manager or VaultManager()
        self.project_root = Path(project_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.patch_history: List[Dict[str, Any]] = []

    def _is_file_safe_for_patching(self, file_path: Path) -> bool:
        """Enforces security boundaries to prevent tampering with auth or environment secrets."""
        resolved = file_path.resolve()
        # Ensure inside project root
        try:
            rel = resolved.relative_to(self.project_root.resolve())
        except ValueError:
            return False

        if resolved.name in BLOCKED_FILES or resolved.suffix in {".pem", ".key", ".token"}:
            return False

        parts = rel.parts
        if not parts:
            return False

        # Allow top-level files like gateway_server.py or files in allowed subdirs
        if parts[0] in ALLOWED_PATCH_DIRS or resolved.name in {"gateway_server.py", "sim_engine.py"}:
            return True

        return False

    def run_tests(
        self,
        test_target: Optional[str] = None,
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        Executes pytest as a subprocess and parses stdout/stderr into structured test metrics.
        """
        cmd = [sys.executable, "-m", "pytest", "-v"]
        if test_target:
            cmd.append(test_target)
        else:
            cmd.append("tests/")

        start_time = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds
            )
            elapsed = round(time.time() - start_time, 2)
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            exit_code = proc.returncode

            # Parse pytest summary line e.g. "46 passed, 1 warning in 3.15s"
            passed = 0
            failed = 0
            total = 0

            summary_match = re.search(r"=+\s*(.*?)\s+in\s+([\d\.]+)s\s*=+", stdout)
            passed_match = re.search(r"(\d+)\s+passed", stdout)
            failed_match = re.search(r"(\d+)\s+failed", stdout)
            collected_match = re.search(r"collected\s+(\d+)\s+items", stdout)

            if passed_match:
                passed = int(passed_match.group(1))
            if failed_match:
                failed = int(failed_match.group(1))
            if collected_match:
                total = int(collected_match.group(1))
            else:
                total = passed + failed

            # Parse failure items from short test summary info
            failures = self.diagnose_failures(stdout)

            pass_rate = round((passed / total * 100), 1) if total > 0 else (100.0 if exit_code == 0 else 0.0)

            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "exit_code": exit_code,
                "passed_all": exit_code == 0,
                "duration_seconds": elapsed,
                "total_tests": total,
                "passed_count": passed,
                "failed_count": failed,
                "pass_rate_percent": pass_rate,
                "failures": failures,
                "stdout_tail": "\n".join(stdout.strip().splitlines()[-15:])
            }

            logger.info(f"🧪 DevLoop test run completed in {elapsed}s: {passed}/{total} passed (exit={exit_code}).")
            return result

        except subprocess.TimeoutExpired:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "exit_code": -1,
                "passed_all": False,
                "duration_seconds": timeout_seconds,
                "total_tests": 0,
                "passed_count": 0,
                "failed_count": 1,
                "pass_rate_percent": 0.0,
                "failures": [{"error": "Test run timed out after timeout period."}],
                "stdout_tail": "SUBPROCESS_TIMEOUT"
            }
        except Exception as e:
            logger.error(f"DevLoop execution exception: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "exit_code": -2,
                "passed_all": False,
                "duration_seconds": round(time.time() - start_time, 2),
                "total_tests": 0,
                "passed_count": 0,
                "failed_count": 1,
                "pass_rate_percent": 0.0,
                "failures": [{"error": str(e)}],
                "stdout_tail": str(e)
            }

    def diagnose_failures(self, pytest_stdout: str) -> List[Dict[str, Any]]:
        """
        Parses pytest output to extract culprit test files, function names, and assertion messages.
        """
        failures = []
        pattern = re.compile(r"FAILED\s+([^\s:]+)::([^\s]+)\s+-\s+(.+)")
        for line in pytest_stdout.splitlines():
            line_str = line.strip()
            match = pattern.search(line_str)
            if match:
                failures.append({
                    "test_file": match.group(1),
                    "test_function": match.group(2),
                    "error_message": match.group(3).strip()
                })
        return failures

    def apply_patch(
        self,
        relative_file_path: str,
        target_content: str,
        replacement_content: str,
        verify_regression: bool = True
    ) -> Dict[str, Any]:
        """
        Atomically replaces target_content with replacement_content in relative_file_path.
        Creates a .bak backup and reverts automatically if regression test fails.
        """
        target_file = (self.project_root / relative_file_path).resolve()
        if not self._is_file_safe_for_patching(target_file):
            raise DevLoopSafetyError(
                f"Security Alert: Auto-patching rejected for blocked or unsafe file: '{relative_file_path}'"
            )

        if not target_file.is_file():
            raise FileNotFoundError(f"Target file does not exist: {relative_file_path}")

        original_text = target_file.read_text(encoding="utf-8")
        if target_content not in original_text:
            return {
                "success": False,
                "error": "Target content snippet not found in target file.",
                "file": relative_file_path,
                "reverted": False
            }

        # Create temporary backup
        backup_file = target_file.with_suffix(f"{target_file.suffix}.bak")
        shutil.copy2(target_file, backup_file)

        # Apply patch
        patched_text = original_text.replace(target_content, replacement_content, 1)
        target_file.write_text(patched_text, encoding="utf-8")

        now_iso = datetime.now(timezone.utc).isoformat()
        patch_record = {
            "timestamp": now_iso,
            "file": relative_file_path,
            "verified": False,
            "rolled_back": False
        }

        if verify_regression:
            test_res = self.run_tests()
            if not test_res["passed_all"]:
                # Regression detected! Revert patch immediately
                shutil.copy2(backup_file, target_file)
                backup_file.unlink(missing_ok=True)
                patch_record["rolled_back"] = True
                logger.warning(f"⚠️ Patch to '{relative_file_path}' caused regression; auto-reverted.")
                return {
                    "success": False,
                    "error": "Patch caused test failures and was automatically rolled back.",
                    "file": relative_file_path,
                    "reverted": True,
                    "test_results": test_res
                }

        # Patch successful and verified
        backup_file.unlink(missing_ok=True)
        patch_record["verified"] = True
        self.patch_history.append(patch_record)

        # Log into Obsidian vault admin logs
        try:
            self.vault_manager.append_admin_log(
                f"🔧 SELF-HEALING AUTO-PATCH: Successfully verified patch on `{relative_file_path}`."
            )
        except Exception:
            pass

        logger.info(f"✅ Self-healing patch applied and verified on '{relative_file_path}'.")
        return {
            "success": True,
            "file": relative_file_path,
            "verified": True,
            "reverted": False
        }

    def execute_self_healing_cycle(self) -> Dict[str, Any]:
        """
        Executes an autonomous test & heal loop:
        1. Runs test suite.
        2. If 100% passing, reports HEALTHY.
        3. If failures exist, returns diagnostic report and recommended candidate patch parameters.
        """
        test_run = self.run_tests()
        if test_run["passed_all"]:
            return {
                "status": "HEALTHY",
                "message": "All test suites passing. System is operating at peak equilibrium.",
                "test_results": test_run,
                "healed": False
            }

        return {
            "status": "DEFECTS_DETECTED",
            "message": f"Detected {test_run['failed_count']} test failure(s). Autonomous diagnostic report prepared.",
            "test_results": test_run,
            "healed": False,
            "recommendation": "Submit targeted candidate patch via /api/v1/devloop/apply-patch."
        }

    def get_health_metrics(self) -> Dict[str, Any]:
        """Computes current ecosystem health metrics."""
        return {
            "status": "ACTIVE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "patches_applied_count": len(self.patch_history),
            "recent_patches": self.patch_history[-5:],
            "healing_agent": "Architect_Prime",
            "safety_boundaries": {
                "allowed_directories": list(ALLOWED_PATCH_DIRS),
                "blocked_files": list(BLOCKED_FILES)
            }
        }

    def stage_and_commit(self, files_to_stage: List[str], commit_message: str) -> Dict[str, Any]:
        """
        Stages specified files and creates an atomic git commit.
        Enforces security boundaries on all staged paths.
        """
        try:
            validated_files = []
            for f in files_to_stage:
                target_path = (self.project_root / f).resolve()
                if not self._is_file_safe_for_patching(target_path):
                    raise DevLoopSafetyError(f"File '{f}' is blocked by security boundaries.")
                validated_files.append(f)

            if not validated_files:
                return {"success": False, "error": "No valid files to stage."}

            # Stage files safely with '--' separation
            add_cmd = ["git", "add", "--"] + validated_files
            subprocess.run(add_cmd, cwd=str(self.project_root), check=True, capture_output=True, text=True)

            # Commit
            commit_cmd = ["git", "commit", "-m", commit_message]
            subprocess.run(commit_cmd, cwd=str(self.project_root), check=True, capture_output=True, text=True)

            # Get hash
            hash_res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(self.project_root), check=True, capture_output=True, text=True)
            commit_hash = hash_res.stdout.strip()

            log_msg = f"🚀 AUTONOMOUS COMMIT: `{commit_hash}` — {commit_message}"
            try:
                self.vault_manager.append_admin_log(log_msg)
            except Exception:
                pass

            return {
                "success": True,
                "commit_hash": commit_hash,
                "message": commit_message
            }
        except (subprocess.CalledProcessError, DevLoopSafetyError) as e:
            err_msg = e.stderr if isinstance(e, subprocess.CalledProcessError) else str(e)
            logger.warning(f"Git commit failed: {err_msg}")
            return {
                "success": False,
                "error": err_msg
            }

    def autonomous_feature_synthesis(
        self,
        task_prompt: str,
        files_to_commit: Optional[List[str]] = None,
        author: str = "Architect_Prime",
        test_target: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Autonomous Feature Authoring (US-021):
        - Analyzes the task requirements
        - Executes master test suite to verify baseline integrity
        - If tests pass and files provided, creates an atomic git commit
        - Logs milestone to Obsidian admin vault
        """
        test_run = self.run_tests(test_target=test_target)

        if not test_run["passed_all"]:
            return {
                "success": False,
                "status": "REGRESSION_DETECTED",
                "message": f"Cannot synthesize feature '{task_prompt}': existing tests failed.",
                "test_results": test_run
            }

        commit_result = None
        if files_to_commit:
            commit_msg = f"feat(auto): {task_prompt} [by {author}]"
            commit_result = self.stage_and_commit(files_to_commit, commit_msg)
            if not commit_result.get("success"):
                return {
                    "success": False,
                    "status": "COMMIT_FAILED",
                    "message": f"Feature tests passed but git commit failed: {commit_result.get('error')}",
                    "commit": commit_result
                }

        return {
            "success": True,
            "task": task_prompt,
            "author": author,
            "test_results": {
                "total": test_run["total_tests"],
                "passed": test_run["passed_count"]
            },
            "commit": commit_result
        }


