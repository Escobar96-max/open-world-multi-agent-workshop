import os
import sys
import json
import datetime
import urllib.request
import urllib.error
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# =====================================================================
# CONFIGURATION & FILE PATHS
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent
TOKEN_FILE_PATH = Path.home() / ".ollama_proxy_token"
VAULT_PATH = BASE_DIR / "ObsidianAgentVault"
EPISODIC_DIR = VAULT_PATH / "01_Episodic_Logs"

# Candidates for backend endpoints
API_ENDPOINTS = [
    "http://localhost:8080/api/memory/consolidate",
    "http://127.0.0.1:8080/api/memory/consolidate",
    "http://localhost:8089/api/memory/consolidate",
    "http://127.0.0.1:8089/api/memory/consolidate"
]

def load_proxy_token() -> str:
    """Safely loads the active secure proxy bypass key from ~/.ollama_proxy_token."""
    if TOKEN_FILE_PATH.exists():
        try:
            return TOKEN_FILE_PATH.read_text(encoding="utf-8").strip()
        except Exception as e:
            print(f"⚠️ Warning reading token file: {e}")
    return os.environ.get("OLLAMA_PROXY_TOKEN", "")

def log_to_obsidian(success: bool, data: dict, error_msg: str = ""):
    """Writes an episodic diary entry to Obsidian recording the consolidation outcome."""
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    target_dir = EPISODIC_DIR / date_str
    target_dir.mkdir(parents=True, exist_ok=True)
    
    time_str = datetime.datetime.now().strftime("%H%M%S")
    log_file = target_dir / f"EP_CRON_CONSOLIDATE_{time_str}.md"
    
    if success:
        stats = data.get("stats", {})
        promoted = data.get("promoted", 0)
        evicted = data.get("evicted", 0)
        retained = data.get("retained", 0)
        compression = stats.get("compression_ratio", 65.0)
        hot_count = stats.get("hot_count", 0)
        cold_count = stats.get("cold_count", 0)
        tombstone_count = stats.get("tombstone_count", 0)

        content = f"""---
type: episodic_log
agent: Memory_Consolidation_Cron_Daemon
timestamp: {datetime.datetime.now().isoformat()}
location: "[[Obsidian_Citadel]]"
tags:
  - episodic_log
  - maintenance
  - cognitive_consolidation
  - cron_job
---

# Episode: Scheduled 3:00 AM Cognitive Memory Consolidation

### Maintenance Telemetry
* **Execution Status**: ✅ SUCCESS
* **Buffer Compression Savings**: {compression}% Token Reduction
* **Promoted to Cold Neocortex**: {promoted} nodes
* **Evicted to Tombstone**: {evicted} items
* **Active Hot Retention**: {retained} logs

### Managed Buffer Snapshot
* **🔥 Hot Buffer (Episodic)**: {hot_count} active diaries
* **❄️ Cold Storage (Facts)**: {cold_count} permanent LATCH nodes
* **🪦 Tombstone (Recycle)**: {tombstone_count} archived entries

### Relations
- [[Project_Manager]]
- [[Obsidian_Citadel]]
- [[00_Central_Command_Index]]
"""
    else:
        content = f"""---
type: episodic_log
agent: Memory_Consolidation_Cron_Daemon
timestamp: {datetime.datetime.now().isoformat()}
location: "[[Obsidian_Citadel]]"
tags:
  - episodic_log
  - maintenance_alert
  - error_trace
---

# Episode: Scheduled Memory Consolidation Warning

### System Alert
* **Execution Status**: ❌ FAILED
* **Error Summary**: {error_msg}
* **Timestamp**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Diagnostic Notes
Ensure the FastAPI backend gateway (port 8080/8089) and secure Ollama proxy (port 11435) are online.

### Relations
- [[Project_Manager]]
- [[Obsidian_Citadel]]
"""
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[✔] Logged maintenance report inside Obsidian: {log_file.name}")

def trigger_consolidation():
    print("=====================================================================")
    print("⏰ RUNNING SCHEDULED 3:00 AM COGNITIVE MEMORY CONSOLIDATION TASK")
    print("=====================================================================")
    
    # 1. Read Active Token
    token = load_proxy_token()
    print(f"[+] Loaded active bypass key: {token[:8]}...[REDACTED]...{token[-8:]}")
    
    # 2. Contact Backend Server
    headers = {
        "Content-Type": "application/json",
        "X-Ollama-Bypass-Token": token,
        "User-Agent": "Antigravity-CronScheduler/2.0"
    }
    
    last_error = ""
    for endpoint in API_ENDPOINTS:
        try:
            print(f"[+] Attempting consolidation trigger on: {endpoint}")
            req = urllib.request.Request(
                endpoint,
                data=json.dumps({}).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=180.0) as resp:
                if resp.status == 200:
                    result_data = json.loads(resp.read().decode("utf-8"))
                    print(f"[✔] Consolidation API call succeeded! Status: {resp.status}")
                    print(f"    - Promoted: {result_data.get('promoted', 0)}")
                    print(f"    - Evicted: {result_data.get('evicted', 0)}")
                    print(f"    - Retained: {result_data.get('retained', 0)}")
                    print(f"    - Compression: {result_data.get('stats', {}).get('compression_ratio', 0)}%")
                    
                    # 3. Log Success to Obsidian
                    log_to_obsidian(True, result_data)
                    print("=====================================================================")
                    print("✨ SCHEDULED CONSOLIDATION MAINTENANCE COMPLETED SUCCESSFULLY!")
                    print("=====================================================================")
                    return True
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='replace')
            last_error = f"HTTP {e.code}: {err_body}"
            print(f"⚠️ Endpoint {endpoint} returned error: {last_error}")
        except Exception as e:
            last_error = str(e)
            print(f"⚠️ Could not reach {endpoint}: {last_error}")

    # Log Failure if all endpoints failed
    print(f"❌ All consolidation endpoints unreachable: {last_error}")
    log_to_obsidian(False, {}, last_error)
    return False

if __name__ == "__main__":
    success = trigger_consolidation()
    sys.exit(0 if success else 1)
