import os
import yaml
import pytest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

def test_dockerfile_configuration():
    dockerfile = ROOT_DIR / "Dockerfile"
    assert dockerfile.is_file(), "Dockerfile must exist at repository root."

    content = dockerfile.read_text(encoding="utf-8")

    # 1. Multi-stage build
    assert "AS builder" in content
    assert "AS runner" in content

    # 2. Non-root user compliance
    assert "appuser" in content
    assert "USER appuser" in content

    # 3. Port & Healthcheck
    assert "EXPOSE 8000" in content
    assert "HEALTHCHECK" in content
    assert "/api/v1/status" in content

def test_docker_compose_structure():
    compose_file = ROOT_DIR / "docker-compose.yml"
    assert compose_file.is_file(), "docker-compose.yml must exist at repository root."

    with open(compose_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "services" in data
    services = data["services"]

    # 1. Gateway Service
    assert "gateway" in services
    gw = services["gateway"]
    assert "8000:8000" in gw["ports"]
    assert any("./vault:/app/vault" in v for v in gw["volumes"])
    assert "healthcheck" in gw

    # 2. Cloudflared Service
    assert "cloudflared" in services
    cf = services["cloudflared"]
    assert "cloudflare/cloudflared" in cf["image"]
    assert "gateway" in cf["depends_on"]

def test_cloudflared_ingress_rules():
    tunnel_file = ROOT_DIR / "cloudflared.yml"
    assert tunnel_file.is_file(), "cloudflared.yml must exist at repository root."

    with open(tunnel_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "tunnel" in data
    assert "ingress" in data
    rules = data["ingress"]
    assert len(rules) >= 2

    # Verify catch-all 404 rule exists at end of ingress table
    last_rule = rules[-1]
    assert last_rule.get("service") == "http_status:404"

def test_dockerignore_coverage():
    ignore_file = ROOT_DIR / ".dockerignore"
    assert ignore_file.is_file(), ".dockerignore must exist at repository root."

    content = ignore_file.read_text(encoding="utf-8")
    assert ".git" in content
    assert ".env" in content
    assert "__pycache__" in content
    assert "*.key" in content
