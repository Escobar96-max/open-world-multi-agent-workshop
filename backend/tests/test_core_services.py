"""
Unit Tests for Core Services:
VaultManager (thread-safe Obsidian CRUD) and VloneDriver (headless web perception).
"""

import os
import sys
from pathlib import Path
import pytest

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import httpx
from app.services.vault_manager import VaultManager, VaultSecurityError
from app.services.vlone_driver import VloneDriver


def test_vault_manager_write_and_recall(tmp_path):
    vault = VaultManager(vault_path=tmp_path)

    # 1. Append valid memory
    note_path = vault.append_memory(
        agent_id="Orion_Prime",
        title="Architecture Strategy Briefing",
        observation="Decomposed autonomous pipeline into 3 distinct worker DAGs.",
        importance=9,
        tags=["strategy", "orchestration"],
        source_url="https://agentworld.local/c2"
    )

    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")
    assert "Architecture Strategy Briefing" in content
    assert "agent: '[[Orion_Prime]]'" in content or 'agent: "[[Orion_Prime]]"' in content
    assert "strategy" in content
    assert "importance: 9" in content

    # 2. Recall memory
    memories = vault.recall_memories(agent_id="Orion_Prime", limit=5)
    assert len(memories) >= 1
    first_mem = memories[0]
    assert first_mem["metadata"]["title"] == "Architecture Strategy Briefing"
    assert first_mem["metadata"]["importance"] == 9

    # 3. Test path traversal rejection
    with pytest.raises(VaultSecurityError):
        vault.append_memory(agent_id="../Hacker_Node", observation="Inject malicious path")

    with pytest.raises(VaultSecurityError):
        vault.append_memory(agent_id="bad id with spaces", observation="Invalid syntax")


def test_vault_lounge_log_stream(tmp_path):
    vault = VaultManager(vault_path=tmp_path)
    vault.append_lounge_log("DJ_Frequency", "Resonating at 432Hz ambient baseline.")

    lounge_file = tmp_path / "World" / "lounge_logs.md"
    assert lounge_file.exists()
    assert "432Hz ambient baseline" in lounge_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_vlone_driver_perception_and_interaction(tmp_path):
    test_url = "https://8.8.8.8/form"

    sample_html = """
    <html>
        <head><title>Mocked Order Form</title></head>
        <body>
            <h1>Customer Intake</h1>
            <form action="/submit" method="post">
                <input type="text" name="customer_name" placeholder="Enter full name" />
                <button type="submit">Submit Order</button>
            </form>
        </body>
    </html>
    """

    mock_transport = httpx.MockTransport(lambda request: httpx.Response(200, text=sample_html))
    driver = VloneDriver(
        sessions_dir=tmp_path / "sessions",
        transport_factory=lambda pinned_map: mock_transport
    )

    # 1. Open page (using in-process soup for deterministic offline test)
    res = await driver.open_page(url=test_url, session_id="test_exec_01", use_playwright=False)
    assert res["session_id"] == "test_exec_01"
    assert "markdown" in res
    assert "elements" in res
    assert res["elements_count"] > 0
    assert res["token_estimate"] > 0

    # Verify first element has data-vlone-id
    first_elem = res["elements"][0]
    assert "vlone_id" in first_elem
    assert first_elem["vlone_id"] == 1

    # 2. Interact with element (fallback engine is read-only and reports unsupported)
    action_res = await driver.interact(
        action="fill",
        vlone_id=1,
        value="Acme Global Distribution",
        session_id="test_exec_01"
    )
    assert action_res["status"] == "unsupported"
    assert "Playwright" in action_res["error"]
    assert action_res["vlone_id"] == 1

    # 3. Get sniffed APIs
    apis = await driver.get_sniffed_apis(session_id="test_exec_01")
    assert isinstance(apis, list)

    # 4. Verify SSRF protection
    with pytest.raises(ValueError):
        await driver.open_page("http://127.0.0.1:8000/secret", session_id="ssrf_test")

    with pytest.raises(ValueError):
        await driver.open_page("http://user:pass@example.com", session_id="ssrf_test")

    with pytest.raises(ValueError):
        await driver.open_page("file:///etc/passwd", session_id="ssrf_test")

    await driver.close()
