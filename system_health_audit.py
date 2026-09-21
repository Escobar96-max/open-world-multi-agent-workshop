#!/usr/bin/env python3
"""
system_health_audit.py: Comprehensive Diagnostic & Health Audit Script for unified_c2_desktop.
Inspects file integrity, vault state, Ollama API, intent classification, and task worker daemons.
"""

import os
import sys
import json
import httpx
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

def check_file(path_str: str):
    p = ROOT_DIR / path_str
    if not p.exists():
        return False, 0, "Missing"
    try:
        lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
        return True, len(lines), "Present"
    except Exception as e:
        return True, 0, f"Error reading: {e}"

def audit_files():
    print("\n" + "="*70)
    print(" 1. ARCHITECTURE & FILE INTEGRITY AUDIT")
    print("="*70)
    target_files = [
        "backend/app/services/executive_duo.py",
        "backend/app/services/vlone_driver.py",
        "backend/app/services/soup_client.py",
        "backend/app/services/vault_manager.py",
        "backend/app/routers/c2_executive.py",
        "backend/app/routers/spatial.py",
        "backend/app/routers/spatial_router.py",
        "ui/src/components/TaskKanban.tsx",
        "ui/src/components/ExecutiveChat.tsx"
    ]
    for tf in target_files:
        exists, line_count, status = check_file(tf)
        status_symbol = "[OK]" if exists else "[FAIL]"
        note = " (Actual router is spatial_router.py)" if tf.endswith("spatial.py") and not exists else ""
        print(f"{status_symbol} {tf:<45} | Lines: {line_count:<6} | {status}{note}")

    # Vault checks
    agents_dir = ROOT_DIR / "vault" / "Agents"
    world_dir = ROOT_DIR / "vault" / "World"

    agent_mds = list(agents_dir.rglob("*.md")) if agents_dir.exists() else []
    world_mds = list(world_dir.rglob("*.md")) if world_dir.exists() else []

    print(f"\n[Vault Markdown Files]")
    print(f"  - vault/Agents/ count: {len(agent_mds)} markdown files across subdirectories")
    print(f"  - vault/World/ count:  {len(world_mds)} markdown files ({', '.join(p.name for p in world_mds)})")

    # Inspect state.md and admin_logs.md
    state_file = world_dir / "state.md"
    admin_logs_file = world_dir / "admin_logs.md"

    print("\n[Last 10 lines of vault/World/state.md]:")
    if state_file.exists():
        lines = state_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        for l in lines[-10:]:
            print(f"  {l}")
    else:
        print("  vault/World/state.md does not exist.")

    print("\n[Last 10 lines of vault/World/admin_logs.md]:")
    if admin_logs_file.exists():
        lines = admin_logs_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        for l in lines[-10:]:
            print(f"  {l}")
    else:
        print("  vault/World/admin_logs.md does not exist (Logs currently streamed to lounge_logs.md and agent memory notes).")

def audit_ollama():
    print("\n" + "="*70)
    print(" 2. OLLAMA LOCAL BRAIN & INTENT ROUTER CHECK")
    print("="*70)
    ollama_url = "http://127.0.0.1:11434/api/tags"
    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.get(ollama_url)
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name") for m in data.get("models", [])]
                print(f"[OK] Ollama is active at {ollama_url}")
                print(f"     Available local models ({len(models)}): {', '.join(models)}")
            else:
                print(f"[WARN] Ollama returned status code {res.status_code}")
    except Exception as e:
        print(f"[FAIL] Could not connect to Ollama at {ollama_url}: {e}")

    # Inspect executive_duo.py for META_QUERY classification
    exec_file = ROOT_DIR / "backend" / "app" / "services" / "executive_duo.py"
    if exec_file.exists():
        content = exec_file.read_text(encoding="utf-8")
        has_meta_query = "META_QUERY" in content
        print(f"\n[Classification Logic Analysis]")
        print(f"  - Mentions META_QUERY explicitly in code: {has_meta_query}")
        
        sys.path.insert(0, str(ROOT_DIR / "backend"))
        try:
            from app.services.executive_duo import classify_intent, TASK_TRIGGER_KEYWORDS
            test_queries = [
                "task gulo complete hote kotokhon lagbe?",
                "task gulo check koro to ki obostha",
                "baki task gulo koto dur holo?",
                "task status ki?",
                "sobai ki kaj korche check koro"
            ]
            print("\n  [Fallback Intent Classifier Simulation]:")
            for tq in test_queries:
                intent = classify_intent(tq)
                triggers = [k for k in TASK_TRIGGER_KEYWORDS if k in tq.lower()]
                print(f"    - '{tq}' -> Intent: {intent:<12} (Trigger matched: {triggers})")
            
            print("\n  [Root Cause for Meta-Query DAG Triggering]:")
            print("    1. In ORION_SYSTEM_PROMPT, there are only TWO discrete output modes specified:")
            print("       - Mode 1: CONVERSATION for greetings and casual chitchat.")
            print("       - Mode 2: TASK for anything involving directives, operations, or tasks.")
            print("       Questions inquiring about ongoing tasks or time estimates ('kotokhon lagbe', 'status check')")
            print("       often trigger the LLM to output {'type': 'TASK', 'tasks': [...]} or trigger fallback keyword 'check',")
            print("       causing Orion to decompose an informational query into a new set of Kanban TaskCards.")
            print("    2. Neither Orion nor Nova's prompt receives the current Kanban task list (self.tasks)")
            print("       in their runtime context, so neither model knows how many tasks are active or pending.")
        except Exception as e:
            print(f"  - Error running classify_intent simulation: {e}")

def audit_task_worker_daemon():
    print("\n" + "="*70)
    print(" 3. TASK WORKER EXECUTION DAEMON CHECK")
    print("="*70)
    c2_router_file = ROOT_DIR / "backend" / "app" / "routers" / "c2_executive.py"
    exec_file = ROOT_DIR / "backend" / "app" / "services" / "executive_duo.py"
    main_file = ROOT_DIR / "backend" / "app" / "main.py"

    c2_code = c2_router_file.read_text(encoding="utf-8") if c2_router_file.exists() else ""
    exec_code = exec_file.read_text(encoding="utf-8") if exec_file.exists() else ""
    main_code = main_file.read_text(encoding="utf-8") if main_file.exists() else ""

    has_asyncio_worker_c2 = "create_task" in c2_code or "background_tasks" in c2_code or "while True" in c2_code
    has_asyncio_worker_exec = "create_task" in exec_code or "worker" in exec_code or "drain" in exec_code
    has_asyncio_worker_main = "create_task" in main_code or "lifespan" in main_code

    print(f"  - Background worker loop in c2_executive.py: {has_asyncio_worker_c2}")
    print(f"  - Background worker loop in executive_duo.py: {has_asyncio_worker_exec}")
    print(f"  - Lifespan / Startup background worker in main.py: {has_asyncio_worker_main}")

    # Inspect task storage
    try:
        from app.services.executive_duo import ExecutiveDuo
        duo = ExecutiveDuo(ollama_enabled=False)
        tasks_state = duo.get_tasks()
        print(f"\n[Default In-Memory Task State on initialization]")
        print(f"  - Total seeded tasks: {tasks_state['total']}")
        print(f"  - In-Progress: {len(tasks_state['in_progress'])}")
        print(f"  - Needs-Approval: {len(tasks_state['needs_approval'])}")
        print(f"  - Completed: {len(tasks_state['completed'])}")
        print("\n  [Root Cause for Frozen In-Progress Tasks]:")
        print("    1. Tasks in self.tasks are purely in-memory data structures.")
        print("    2. When process_directive creates TaskCards with status='in_progress', NO asynchronous")
        print("       background worker task (asyncio.create_task) is dispatched to process or drain them.")
        print("    3. There is no scheduler or auto-completion timer. Tasks only advance to 'completed'")
        print("       when the user explicitly sends an HTTP POST request to /api/v1/c2/tasks/complete.")
        print("    4. Sub-agents (Architect_Prime, Sentinel_Alpha, Vlone_Browser, Soup_Zero, DJ_Frequency)")
        print("       have service classes (VloneDriver, SoupZeroEngine, SpatialGrid), but no unified autonomous")
        print("       job queue manager connects in_progress TaskCards to actual service execution.")
    except Exception as e:
        print(f"  - Error testing ExecutiveDuo tasks: {e}")

if __name__ == "__main__":
    audit_files()
    audit_ollama()
    audit_task_worker_daemon()
    print("\n" + "="*70)
    print(" AUDIT EXECUTION COMPLETED")
    print("="*70 + "\n")
