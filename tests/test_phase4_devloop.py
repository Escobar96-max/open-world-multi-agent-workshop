import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import FastAPI

from services.dev_loop import DevLoopEngine, DevLoopSafetyError
from services.vault_manager import VaultManager
from api.devloop_router import router as devloop_router

app = FastAPI()
app.include_router(devloop_router)
client = TestClient(app)

@pytest.fixture
def dev_engine(tmp_path):
    vm = VaultManager(vault_root=str(tmp_path / "vault"))
    vm.ensure_vault_hierarchy()
    engine = DevLoopEngine(vault_manager=vm)
    return engine

def test_run_tests_execution(dev_engine):
    # Run a quick sub-suite
    res = dev_engine.run_tests(test_target="tests/test_dj_frequency.py", timeout_seconds=30)
    assert res["exit_code"] == 0
    assert res["passed_all"] is True
    assert res["passed_count"] >= 3
    assert res["pass_rate_percent"] == 100.0
    assert res["duration_seconds"] > 0

def test_safety_boundary_blocks_critical_files(dev_engine):
    # Attempting to patch gatekeeper.py must be rejected
    with pytest.raises(DevLoopSafetyError):
        dev_engine.apply_patch(
            relative_file_path="services/gatekeeper.py",
            target_content="dummy",
            replacement_content="dummy"
        )

    # Attempting to patch .env must be rejected
    with pytest.raises(DevLoopSafetyError):
        dev_engine.apply_patch(
            relative_file_path=".env",
            target_content="dummy",
            replacement_content="dummy"
        )

def test_patch_application_and_rollback(dev_engine, tmp_path):
    # Create test scratch file in services/
    scratch_file = dev_engine.project_root / "services" / "_test_scratch_target.py"
    try:
        scratch_file.write_text("def test_fn():\n    return 'alpha'\n", encoding="utf-8")
        rel_path = "services/_test_scratch_target.py"

        # 1. Apply valid patch without regression check
        res = dev_engine.apply_patch(
            relative_file_path=rel_path,
            target_content="return 'alpha'",
            replacement_content="return 'beta'",
            verify_regression=False
        )
        assert res["success"] is True
        assert "return 'beta'" in scratch_file.read_text(encoding="utf-8")

        # 2. Target content not found
        res_missing = dev_engine.apply_patch(
            relative_file_path=rel_path,
            target_content="return 'gamma_nonexistent'",
            replacement_content="return 'delta'",
            verify_regression=False
        )
        assert res_missing["success"] is False
        assert "not found" in res_missing["error"]

    finally:
        if scratch_file.exists():
            scratch_file.unlink()
        bak = scratch_file.with_suffix(".py.bak")
        if bak.exists():
            bak.unlink()

def test_health_metrics_and_healing_cycle(dev_engine):
    metrics = dev_engine.get_health_metrics()
    assert metrics["status"] == "ACTIVE"
    assert metrics["healing_agent"] == "Architect_Prime"
    assert "services" in metrics["safety_boundaries"]["allowed_directories"]

def test_api_devloop_endpoints(monkeypatch):
    from api import devloop_router as dr
    test_dev_loop = DevLoopEngine()
    monkeypatch.setattr(dr, "dev_loop", test_dev_loop)

    # 1. GET /api/v1/devloop/health
    resp = client.get("/api/v1/devloop/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"

    # 2. POST /api/v1/devloop/run-tests
    resp = client.post(
        "/api/v1/devloop/run-tests",
        json={"target": "tests/test_dj_frequency.py", "timeout_seconds": 30}
    )
    assert resp.status_code == 200
    assert resp.json()["exit_code"] == 0
    assert resp.json()["passed_all"] is True
