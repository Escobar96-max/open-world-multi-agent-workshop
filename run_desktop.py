"""
Antigravity Unified C2 Desktop - Master Application Launcher
Launches FastAPI backend on 127.0.0.1:8000 and opens the native desktop GUI via pywebview.
"""

import os
import sys
import time
import argparse
import threading
import urllib.request
import json
from pathlib import Path

# Add backend directory to sys.path
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

try:
    import uvicorn
    from app.main import app
    from app.config import settings
except ImportError as e:
    print(f"[Launcher Error] Failed to import backend modules: {e}")
    sys.exit(1)


def run_backend(host: str, port: int):
    """Run Uvicorn FastAPI server in background thread."""
    config = uvicorn.Config(app=app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    server.run()


def wait_for_server(url: str, timeout: float = 15.0) -> bool:
    """Wait for FastAPI server to respond."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=1.0) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def run_self_test(host: str, port: int) -> bool:
    """Validate all core endpoints and subsystem health for test-mode."""
    base_url = f"http://{host}:{port}"
    print(f"\n[Test Mode] Running comprehensive system self-test on {base_url}...")

    endpoints = [
        ("/health", "Healthcheck"),
        ("/api/v1/system/status", "System Status"),
        ("/api/v1/spatial/state", "2D Spatial Grid & DJ State"),
        ("/api/v1/c2/tasks", "Task Kanban Rail"),
        ("/api/v1/c2/groups", "Executive Sub-Team Groups"),
        ("/api/v1/vlone/state", "VLONE Engine State")
    ]

    for path, label in endpoints:
        try:
            req = urllib.request.Request(f"{base_url}{path}")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode())
                print(f"  [PASS] {label} ({path}) -> Status {resp.status}")
        except Exception as e:
            print(f"  [FAIL] {label} ({path}) -> {e}")
            return False

    # Check React Frontend Root
    try:
        req = urllib.request.Request(f"{base_url}/")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            content = resp.read().decode("utf-8")
            if resp.status == 200 and ("<div id=\"root\">" in content or "html" in content.lower()):
                print(f"  [PASS] React Frontend GUI (/) -> Status {resp.status} (Bundle verified)")
            else:
                print(f"  [FAIL] React Frontend GUI (/) -> Status {resp.status} (Unexpected content)")
                return False
    except Exception as e:
        print(f"  [FAIL] React Frontend GUI (/) -> {e}")
        return False

    print("\n[Test Mode] All subsystems operational! Orion Prime & Nova are live.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Antigravity Unified C2 Desktop Launcher")
    parser.add_argument("--test-mode", action="store_true", help="Run self-test suite and exit")
    parser.add_argument("--no-window", action="store_true", help="Run backend server only without native window")
    parser.add_argument("--port", type=int, default=8000, help="Port for C2 Backend (default: 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")

    args = parser.parse_args()

    print("===================================================================")
    print("  ANTIGRAVITY UNIFIED C2 EXECUTIVE DESK")
    print("  Orion Prime (Chief) | Nova (Executive Assistant)")
    print("  Spatial World [0-100] | 432Hz Lounge | VLONE Semantic Browser")
    print("===================================================================")

    # Start backend daemon
    print(f"[Launcher] Starting FastAPI backend on http://{args.host}:{args.port}...")
    server_thread = threading.Thread(
        target=run_backend,
        args=(args.host, args.port),
        daemon=True
    )
    server_thread.start()

    # Wait for backend readiness
    server_url = f"http://{args.host}:{args.port}"
    if not wait_for_server(server_url):
        print(f"[Launcher Error] Backend failed to start within timeout at {server_url}")
        sys.exit(1)

    print(f"[Launcher] Backend is online and healthy at {server_url}!")

    # If in test mode, run verification and exit
    if args.test_mode:
        success = run_self_test(args.host, args.port)
        if success:
            print("[Test Mode] Exiting successfully.")
            sys.exit(0)
        else:
            print("[Test Mode] Self-test reported failures.")
            sys.exit(1)

    # Native Window Launch via pywebview
    if not args.no_window:
        try:
            import webview
            print("[Launcher] Launching native desktop window via pywebview...")
            window = webview.create_window(
                title="Antigravity Unified C2 Executive Desk",
                url=server_url,
                width=1440,
                height=920,
                resizable=True,
                min_size=(1024, 700)
            )
            webview.start()
            print("[Launcher] Native window closed. Shutting down...")
        except ImportError:
            print("[Launcher Warning] pywebview not installed. Opening default browser instead.")
            import webbrowser
            webbrowser.open(server_url)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("[Launcher] Shutting down...")
    else:
        print(f"[Launcher] Running in headless server mode at {server_url}. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[Launcher] Shutting down...")


if __name__ == "__main__":
    main()
