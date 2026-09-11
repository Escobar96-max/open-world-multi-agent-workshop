import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from services.soup_client import SoupClient
from services.vault_manager import VaultManager
from api.sanctum_router import router as sanctum_router

app = FastAPI()
app.include_router(sanctum_router)
client = TestClient(app)

@pytest.fixture
def temp_vault(tmp_path):
    vm = VaultManager(vault_root=str(tmp_path))
    vm.ensure_vault_hierarchy()
    # Seed agent profile
    vm.ensure_agent_structure("Sentinel_Alpha")
    vm.write_agent_profile("Sentinel_Alpha", {"name": "Sentinel Alpha", "level": 1, "xp": 0, "badges": []}, "# Sentinel Alpha Profile")
    return vm

def test_modules_listing_and_details():
    soup = SoupClient()
    modules = soup.get_modules()
    assert len(modules) >= 4
    mod_ids = [m["id"] for m in modules]
    assert "fibonacci_recursion" in mod_ids
    assert "spatial_manhattan_distance" in mod_ids
    assert "token_escrow_validator" in mod_ids
    assert "vector_cosine_similarity" in mod_ids

    fib_mod = soup.get_module("fibonacci_recursion")
    assert fib_mod is not None
    assert fib_mod["entry_function"] == "fib"

def test_ast_security_sandbox(temp_vault):
    soup = SoupClient(vault_manager=temp_vault)
    
    # 1. Test forbidden import
    malicious_code1 = "import os\ndef fib(n):\n    os.system('echo hacked')\n    return n\n"
    res1 = soup.evaluate_code("fibonacci_recursion", malicious_code1)
    assert res1["success"] is False
    assert "Prohibited module" in res1["error"]
    assert res1["reward"] == 0.0

    # 2. Test forbidden exec/eval
    malicious_code2 = "def fib(n):\n    eval('2 + 2')\n    return n\n"
    res2 = soup.evaluate_code("fibonacci_recursion", malicious_code2)
    assert res2["success"] is False
    assert "Prohibited function execution" in res2["error"]

def test_evaluation_correct_and_incorrect(temp_vault):
    soup = SoupClient(vault_manager=temp_vault)

    # Correct solution for fibonacci
    good_code = """
def fib(n: int) -> int:
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""
    res = soup.evaluate_code("fibonacci_recursion", good_code)
    assert res["success"] is True
    assert res["reward"] == 1.0
    assert res["tests_passed"] == 5

    # Incorrect solution (always returns 0)
    bad_code = "def fib(n: int) -> int:\n    return 0\n"
    res_bad = soup.evaluate_code("fibonacci_recursion", bad_code)
    assert res_bad["success"] is False
    assert res_bad["reward"] < 0.8
    assert res_bad["tests_passed"] == 1  # only fib(0)==0 passes

def test_full_submission_graduation_and_leaderboard(temp_vault):
    soup = SoupClient(vault_manager=temp_vault)

    good_code = """
def manhattan_distance(p1: tuple, p2: tuple) -> float:
    return float(abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]))
"""
    result = soup.process_solution_submission("Sentinel_Alpha", "spatial_manhattan_distance", good_code)
    assert result["status"] == "GRADUATED"
    assert result["graduated"] is True
    assert result["xp_awarded"] == 60
    assert result["total_xp"] == 60
    assert "sanctum_spatial_manhattan_distance" in result["badge_earned"]

    # Verify agent profile updated in vault
    fm, _ = temp_vault.get_agent_profile("Sentinel_Alpha")
    assert fm["xp"] == 60
    assert "sanctum_spatial_manhattan_distance" in fm["badges"]

    # Verify leaderboard updated
    board = soup.get_leaderboard()
    assert board["total_agents"] >= 1
    agent_entry = next(e for e in board["standings"] if e["agent_id"] == "Sentinel_Alpha")
    assert agent_entry["xp"] == 60
    assert "spatial_manhattan_distance" in agent_entry["completed_modules"]

def test_sanctum_api_endpoints(temp_vault, monkeypatch):
    # Route sanctum_router dependencies to temp_vault
    from api import sanctum_router as sr
    test_soup = SoupClient(vault_manager=temp_vault)
    monkeypatch.setattr(sr, "soup_client", test_soup)
    monkeypatch.setattr(sr, "vault_mgr", temp_vault)

    # 1. GET /modules
    resp = client.get("/api/v1/sanctum/modules")
    assert resp.status_code == 200
    data = resp.json()
    assert "modules" in data
    assert len(data["modules"]) >= 4

    # 2. POST /enter
    resp = client.post("/api/v1/sanctum/enter", json={"agent_id": "Sentinel_Alpha"})
    assert resp.status_code == 200
    enter_data = resp.json()
    assert enter_data["status"] == "ADMITTED"
    assert enter_data["agent_id"] == "Sentinel_Alpha"

    # 3. POST /submit-solution (Pass)
    solution = """
def validate_transaction(sender_balance: float, amount: float, fee: float) -> tuple:
    if amount <= 0 or fee < 0:
        return (False, sender_balance)
    total = amount + fee
    if total > sender_balance:
        return (False, sender_balance)
    return (True, sender_balance - total)
"""
    resp = client.post(
        "/api/v1/sanctum/submit-solution",
        json={
            "agent_id": "Sentinel_Alpha",
            "module_id": "token_escrow_validator",
            "code": solution
        }
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "GRADUATED"
    assert res_data["graduated"] is True

    # 4. GET /leaderboard
    resp = client.get("/api/v1/sanctum/leaderboard")
    assert resp.status_code == 200
    board_data = resp.json()
    assert board_data["total_agents"] >= 1
