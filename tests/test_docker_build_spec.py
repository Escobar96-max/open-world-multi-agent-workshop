import os
import re
import yaml
import pytest
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from gateway_server import app

def test_dockerfile_multi_stage_architecture():
    """Verify that Dockerfile implements a secure, hardened multi-stage build."""
    dockerfile_path = ROOT_DIR / "Dockerfile"
    assert dockerfile_path.is_file(), "Dockerfile must be present in repository root."
    
    lines = dockerfile_path.read_text(encoding="utf-8").splitlines()
    
    # 1. Builder Stage
    builder_stages = [l for l in lines if re.match(r"^FROM\s+python:.*AS\s+builder", l, re.IGNORECASE)]
    assert len(builder_stages) == 1, "Must have exactly one builder stage."
    
    # 2. Runner Stage
    runner_stages = [l for l in lines if re.match(r"^FROM\s+python:.*AS\s+runner", l, re.IGNORECASE)]
    assert len(runner_stages) == 1, "Must have exactly one minimal runner stage."
    
    content = "\n".join(lines)
    
    # 3. Build essentials only in builder
    builder_part = content.split("FROM python:3.11-slim AS runner")[0]
    runner_part = content.split("FROM python:3.11-slim AS runner")[1]
    
    assert "build-essential" in builder_part, "Builder stage must install build tools."
    assert "build-essential" not in runner_part, "Runner stage must not include build-essential."
    
    # 4. Layer caching: requirements.txt copied before source code
    copy_req_idx = -1
    copy_src_idx = -1
    for idx, l in enumerate(lines):
        if "COPY requirements.txt" in l:
            copy_req_idx = idx
        if "COPY --chown=appuser:appgroup . /app" in l:
            copy_src_idx = idx
            
    assert copy_req_idx != -1, "Must copy requirements.txt for layer caching."
    assert copy_src_idx != -1, "Must copy application code."
    assert copy_req_idx < copy_src_idx, "requirements.txt must be copied before application code for optimal layer caching."

def test_dockerfile_security_and_non_root():
    """Verify that runner stage drops privileges to unprivileged appuser (UID 10001)."""
    dockerfile = ROOT_DIR / "Dockerfile"
    content = dockerfile.read_text(encoding="utf-8")
    
    # Non-root user creation
    assert "groupadd -g 10001 appgroup" in content
    assert "useradd -u 10001 -g appgroup" in content
    assert "USER appuser" in content
    
    # Ensure root cannot run the container
    user_directives = [l.strip() for l in content.splitlines() if l.strip().startswith("USER ")]
    assert user_directives[-1] == "USER appuser", "Final USER directive must be unprivileged 'appuser'."

def test_dockerfile_healthcheck_target():
    """Verify that Dockerfile HEALTHCHECK targets a valid endpoint that returns 200 OK."""
    dockerfile = ROOT_DIR / "Dockerfile"
    content = dockerfile.read_text(encoding="utf-8")
    
    # Assert HEALTHCHECK directive presence
    assert "HEALTHCHECK" in content
    assert "CMD curl -f http://localhost:8000/api/v1/status || exit 1" in content
    
    # Test that the target endpoint responds with 200 and valid JSON
    client = TestClient(app)
    res = client.get("/api/v1/status")
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "ONLINE"
    assert "world_tick" in data

def test_docker_compose_production_spec():
    """Verify production docker-compose specifications."""
    compose_path = ROOT_DIR / "docker-compose.yml"
    assert compose_path.is_file()
    
    with open(compose_path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
        
    services = spec.get("services", {})
    assert "gateway" in services, "gateway service must be defined."
    assert "cloudflared" in services, "cloudflared service must be defined."
    
    gw = services["gateway"]
    build_spec = gw.get("build")
    assert build_spec == "." or (isinstance(build_spec, dict) and build_spec.get("context") == "."), "gateway must build from local Dockerfile context."
    assert "8000:8000" in gw.get("ports", []), "gateway must expose port 8000."
    assert any("./vault:/app/vault" in v for v in gw.get("volumes", [])), "Must mount vault volume."
    assert gw.get("restart") in ["always", "unless-stopped"], "Production restart policy must be enabled."

def test_dockerignore_security():
    """Verify that secret keys, git history, and build caches are excluded from docker context."""
    ignore_path = ROOT_DIR / ".dockerignore"
    assert ignore_path.is_file()
    
    entries = [line.strip() for line in ignore_path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
    
    critical_exclusions = [".git", ".env", "__pycache__", "*.pyc", "*.key", ".pytest_cache"]
    for crit in critical_exclusions:
        assert any(crit in entry for entry in entries), f"Critical exclusion '{crit}' missing from .dockerignore."

if __name__ == "__main__":
    sys.exit(pytest.main([str(Path(__file__).resolve()), "-v"]))
