"""
Unified C2 Desktop Configuration
Settings for FastAPI daemon, Antigravity Spatial Grid, Obsidian Vault, and VLONE Headless Browser.
"""

import os
import secrets
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
VAULT_DIR = Path(os.getenv("VAULT_PATH", str(BASE_DIR / "vault")))
SESSIONS_DIR = Path(os.getenv("VLONE_SESSIONS_DIR", str(BASE_DIR / "vlone_sessions")))


class Settings(BaseModel):
    app_name: str = "Unified C2 Desktop Platform"
    app_version: str = "3.0.0"
    server_host: str = os.getenv("HOST", "127.0.0.1")
    server_port: int = int(os.getenv("PORT", "8000"))
    admin_secret_key: str = os.getenv("ADMIN_SECRET_KEY") or secrets.token_hex(32)

    # Antigravity 2D Spatial World Boundaries
    grid_min: float = 0.0
    grid_max: float = 100.0
    work_plaza_max: float = 50.0
    lounge_min: float = 51.0
    proximity_threshold: float = 5.0
    work_plaza_temp: float = 0.2
    lounge_temp: float = 1.6
    simulation_tick_interval: float = 5.0

    # Local Engine & AI Endpoints
    ollama_url: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    preferred_model: str = os.getenv("OLLAMA_MODEL", "llama3.2:latest")

    # Vault & Session Storage
    vault_path: Path = VAULT_DIR
    sessions_path: Path = SESSIONS_DIR


settings = Settings()

# Ensure critical directories exist
settings.vault_path.mkdir(parents=True, exist_ok=True)
settings.sessions_path.mkdir(parents=True, exist_ok=True)
