import os
import sys
import secrets
import datetime
from pathlib import Path

# Ensure UTF-8 console output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# =====================================================================
# CONFIGURATION & FILE PATHS
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE_PATH = Path.home() / ".ollama_proxy_token"
ENV_FILE_PATH = BASE_DIR / ".env"
DEPENDENT_CONFIGS = [
    BASE_DIR / "dev_project_v2" / ".env",
    BASE_DIR / "open-world-multi-agent-workshop" / ".env",
]
VAULT_PATH = BASE_DIR / "ObsidianAgentVault"

def generate_secure_token() -> str:
    """Generates a cryptographically secure 32-byte hex token."""
    return secrets.token_hex(32)

def write_proxy_token(token: str):
    """Writes the token securely to the primary proxy file with restricted permissions."""
    TOKEN_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(token.strip())
    
    try:
        os.chmod(TOKEN_FILE_PATH, 0o600)
    except Exception as e:
        pass

def update_env_files(token: str):
    """Updates or creates .env files with the new token for backend servers and agent scripts."""
    configs_to_update = [ENV_FILE_PATH] + DEPENDENT_CONFIGS
    
    for config_path in configs_to_update:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        env_lines = []
        token_line_written = False
        
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("OLLAMA_PROXY_TOKEN=") or line.strip().startswith("OLLAMA_BYPASS_TOKEN="):
                        env_lines.append(f"OLLAMA_PROXY_TOKEN={token}\n")
                        env_lines.append(f"OLLAMA_BYPASS_TOKEN={token}\n")
                        token_line_written = True
                    else:
                        env_lines.append(line)
        
        if not token_line_written:
            env_lines.append(f"OLLAMA_PROXY_TOKEN={token}\n")
            env_lines.append(f"OLLAMA_BYPASS_TOKEN={token}\n")
            
        with open(config_path, "w", encoding="utf-8") as f:
            f.writelines(env_lines)
            
        print(f"[✔] Successfully synchronized token with environment config: {config_path}")

def log_rotation_event():
    """Logs the rotation event to our central Obsidian daily notes for agent awareness."""
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    episodic_dir = VAULT_PATH / "01_Episodic_Logs" / date_str
    episodic_dir.mkdir(parents=True, exist_ok=True)
    
    time_str = datetime.datetime.now().strftime("%H%M%S")
    log_file = episodic_dir / f"EP_SEC_ROTATOR_{time_str}.md"
    
    log_content = f"""---
type: episodic_log
agent: Security_Rotator_Daemon
timestamp: {datetime.datetime.now().isoformat()}
location: "[[Obsidian_Citadel]]"
tags:
  - episodic_log
  - system_security
  - token_rotation
---

# Episode: Secure Token Rotated Autopilot Execution

### System Alert
*   **Action**: 24-Hour Automated Token Rotation
*   **Status**: Active & Synchronized
*   **Security Context**: Secure loopback proxy secrets and downstream agent files have been updated.

### Execution Log
The system has generated a new secure proxy validation token and written it to `~/.ollama_proxy_token`.
Downstream agent workspaces and the local FastAPI communication backend have been hot-synchronized with the rotated token.

### Relations
- [[Project_Manager]]
- [[Obsidian_Citadel]]
"""
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(log_content)
    print(f"[✔] Logged rotation event inside Obsidian: {log_file}")

def main():
    print("=====================================================================")
    print("STARTING AUTOPILOT OLLAMA PROXY TOKEN ROTATION ENGINE")
    print("=====================================================================")
    
    # 1. Generate new token
    new_token = generate_secure_token()
    print(f"[+] Generated secure 256-bit token: {new_token[:8]}...[REDACTED]...{new_token[-8:]}")
    
    # 2. Write to master proxy location
    write_proxy_token(new_token)
    print(f"[✔] Successfully wrote new master token to: {TOKEN_FILE_PATH}")
    
    # 3. Synchronize with downstream environment profiles
    update_env_files(new_token)
    
    # 4. Write back episodic telemetry to Obsidian daily diaries
    log_rotation_event()
    
    print("=====================================================================")
    print("TOKEN ROTATION COMPLETED SUCCESSFULLY. SYSTEM FULLY SECURED.")
    print("=====================================================================")

if __name__ == "__main__":
    main()
