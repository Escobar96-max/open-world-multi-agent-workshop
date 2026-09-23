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
from app.services.vlone_driver import VloneDriver, VloneUpgradedDriver


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


@pytest.mark.asyncio
async def test_vlone_upgraded_driver_stealth_and_init(tmp_path):
    """
    Verifies VloneUpgradedDriver:
    1. Initializes with stealth shielding removing navigator.webdriver
    2. Provides chrome runtime and plugins
    3. Handles auto_scroll and session state saving
    """
    driver = VloneUpgradedDriver(session_id="workspace_gmail", headless=True)
    driver.session_dir = tmp_path
    driver.session_file = tmp_path / "workspace_gmail_state.json"

    try:
        await driver.initialize()
        assert driver.active_page is not None

        # 1. Verify navigator.webdriver is undefined
        webdriver_val = await driver.active_page.evaluate("() => navigator.webdriver")
        assert webdriver_val is None or webdriver_val is False

        # 2. Verify window.chrome runtime and plugins
        chrome_exists = await driver.active_page.evaluate("() => Boolean(window.chrome && window.chrome.runtime)")
        assert chrome_exists is True

        plugins_len = await driver.active_page.evaluate("() => navigator.plugins.length")
        assert plugins_len > 0

        # 3. Verify auto_scroll & human_type interfaces
        await driver.auto_scroll(max_scrolls=1, delay_ms=10)

        # 4. Verify session vault persistence
        await driver.save_session_vault()
        assert driver.session_file.exists()
    finally:
        await driver.close()


@pytest.mark.asyncio
async def test_vlone_upgraded_selective_sniffer(tmp_path):
    """
    Verifies selective network sniffer:
    1. Discards analytics, tracking, telemetry, and pixel blobs
    2. Retains high-value API endpoints (wp-json, api/v, users, team)
    """
    driver = VloneUpgradedDriver(session_id="osint_social", headless=True)
    driver.session_dir = tmp_path
    driver.session_file = tmp_path / "osint_social_state.json"

    class MockResponse:
        def __init__(self, url: str, status: int = 200, body: str = '{"status": "ok"}'):
            self.url = url
            self.status = status
            self._body = body

        async def text(self):
            return self._body

    # Simulate responses through sniffer callback
    class MockPage:
        def __init__(self):
            self.handlers = []

        def on(self, event, handler):
            if event == "response":
                self.handlers.append(handler)

        async def emit_response(self, resp):
            for h in self.handlers:
                await h(resp)

    mock_page = MockPage()
    driver._attach_selective_sniffer(mock_page)

    # 1. Telemetry noise (should be ignored)
    await mock_page.emit_response(MockResponse("https://example.com/analytics/v2/collect"))
    await mock_page.emit_response(MockResponse("https://example.com/tr/facebook-pixel.gif"))
    await mock_page.emit_response(MockResponse("https://telemetry.service.com/track"))
    await mock_page.emit_response(MockResponse("https://ad.doubleclick.net/pixel"))

    assert len(driver.sniffed_apis) == 0

    # 2. High-value endpoints (should be captured)
    await mock_page.emit_response(MockResponse("https://example.com/wp-json/wp/v2/users", body='[{"name": "Admin"}]'))
    await mock_page.emit_response(MockResponse("https://example.com/api/v1/leadership", body='{"ceo": "Sarah"}'))
    await mock_page.emit_response(MockResponse("https://example.com/graphql", body='{"data": {"team": []}}'))

    assert len(driver.sniffed_apis) == 3
    urls = [api["url"] for api in driver.sniffed_apis]
    assert any("wp-json" in u for u in urls)
    assert any("api/v1" in u for u in urls)
    assert any("graphql" in u for u in urls)

