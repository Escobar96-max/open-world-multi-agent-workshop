"""
Integration and Unit Tests for:
Autonomous Executive Lead Engine (Laila + Moly)
- MolyLeadEngine (4-Tier Waterfall Radar, ReacherHQ SMTP, agent-reach, PhoneInfoga, Vlone Google Sheets Sync)
- LailaSupervisor (ICP Criteria Translation, Task Delegation, Quality QA, Proactive Banglish Alerts)
- REST API Endpoints & C2 Desk Integration
"""

import json
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from app.services.moly_lead_hunter import MolyLeadEngine, moly_agent
from app.services.laila_supervisor import LailaSupervisor, laila_manager
from app.services.executive_duo import ExecutiveDuo
from app.routers.c2_executive import get_executive_duo


@pytest.fixture
def lead_engine(tmp_path):
    return MolyLeadEngine(vault_path=tmp_path)


@pytest.fixture
def supervisor():
    return LailaSupervisor()


@pytest.mark.asyncio
async def test_tier1_wp_json_and_schema_org(lead_engine):
    # 1. Test Schema.org JSON-LD extraction
    mock_html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "Lone Star Logistics LLC",
          "founder": {
            "@type": "Person",
            "name": "Marcus Vance",
            "jobTitle": "Chief Executive Officer & Founder"
          }
        }
        </script>
      </head>
      <body><h1>Lone Star Logistics</h1></body>
    </html>
    """
    res = await lead_engine.tier1_deep_sweep(
        target_url="https://lonestarfreight.com",
        html_content=mock_html
    )
    assert res is not None
    assert "Marcus Vance" in res["name"]
    assert "Tier 1B" in res["source"]

    # 2. Test Background Sniffed Network Payload
    sniffed_logs = [
        {
            "url": "https://lonestarfreight.com/api/v1/leadership",
            "response_body": json.dumps({"director": "Clayton Brooks", "title": "President & Director"})
        }
    ]
    sniff_res = await lead_engine.tier1_deep_sweep(
        target_url="https://lonestarfreight.com",
        network_logs=sniffed_logs
    )
    assert sniff_res is not None
    assert "Clayton Brooks" in sniff_res["name"]
    assert "Sniffed Backend" in sniff_res["source"]


@pytest.mark.asyncio
async def test_tier2_social_reach(lead_engine):
    res = await lead_engine.tier2_social_reach("Texas Logistics Group", "texaslogistics.com")
    assert res is not None
    assert res["name"] == "Clayton Brooks"
    assert "Chief Executive Officer" in res["title"]
    assert "agent-reach" in res["source"]
    assert "linkedin.com" in res["social_url"]


@pytest.mark.asyncio
async def test_tier3_and_tier4_fallbacks(lead_engine):
    t3 = await lead_engine.tier3_media_mining("Freight Masters", "freightmasters.com")
    assert t3 is not None
    assert "Sarah Jenkins" in t3["name"]
    assert "Tier 3" in t3["source"]

    t4 = await lead_engine.tier4_registry_failover("Freight Masters", state="TX")
    assert t4 is not None
    assert "Robert T. McCallister" in t4["name"]
    assert "Secretary of State" in t4["source"]


def test_email_permutations_and_phone_audit(lead_engine):
    perms = lead_engine.generate_email_permutations("Marcus Vance", "https://directfreight.com/")
    assert len(perms) >= 4
    assert "marcus@directfreight.com" in perms
    assert "marcus.vance@directfreight.com" in perms
    assert "ceo@directfreight.com" in perms

    phone_info = lead_engine.audit_phone_line("+1 (512) 894-2101")
    assert phone_info["is_deliverable"] is True
    assert phone_info["line_type"] == "MOBILE"
    assert "Texas Enterprise" in phone_info["carrier"]


@pytest.mark.asyncio
async def test_reacherhq_smtp_handshake(lead_engine):
    # Safe verification test
    valid = await lead_engine.verify_smtp("marcus.vance@directfreight.com")
    assert valid is True

    # Invalid email
    invalid = await lead_engine.verify_smtp("not-an-email")
    assert invalid is False


@pytest.mark.asyncio
async def test_moly_harvest_and_vault_backup(lead_engine):
    domains = [
        {"company": "Direct Freight Express", "domain": "directfreight.com"},
        {"company": "Texas Logistics Group", "domain": "texaslogistics.com"}
    ]
    res = await lead_engine.harvest_leads(
        niche="Texas Logistics CEOs",
        target_domains=domains,
        target_sheet_url="https://docs.google.com/spreadsheets/d/test-sheet-id/edit"
    )
    assert res["total_leads"] == 2
    assert len(res["leads"]) == 2
    first_lead = res["leads"][0]
    assert first_lead["verified_smtp"] is True
    assert "@" in first_lead["email"]

    # Verify local Obsidian vault backup file
    vault_file = Path(res["vault_backup"])
    assert vault_file.exists()
    content = vault_file.read_text(encoding="utf-8")
    assert "Moly Autonomous Lead Harvest" in content
    assert "[[Laila]]" in content
    assert "[[Moly]]" in content
    assert "Direct Freight Express" in content


def test_laila_supervisor_icp_translation(supervisor):
    directive = "Find Texas Logistics CEOs and B2B Freight Warehouses with $10M+ ARR"
    icp = supervisor.parse_icp_criteria(directive)
    assert "Texas, USA" in icp["location"]
    assert "Logistics" in icp["niche"]
    assert "Chief Executive Officer" in icp["titles"]

    reassurance = supervisor.generate_instant_reassurance("Texas Logistics")
    assert "Chill Boss" in reassurance
    assert "Moly" in reassurance
    assert "ReacherHQ SMTP" in reassurance

    alert = supervisor.generate_proactive_completion_alert(
        niche="Texas Logistics",
        count=15,
        sheet_url="https://docs.google.com/spreadsheets/d/test/edit"
    )
    assert "Boss! Moly task complete koreche!" in alert
    assert "ReacherHQ Rust SMTP" in alert
    assert "https://docs.google.com/spreadsheets/d/test/edit" in alert


@pytest.mark.asyncio
async def test_laila_lead_campaign_execution(supervisor):
    res = await supervisor.execute_lead_campaign(
        niche="Texas Freight Warehouses",
        criteria="C-Suite Only",
        target_sheet_url="https://docs.google.com/spreadsheets/d/test-sheet/edit"
    )
    assert res["status"] == "COMPLETED"
    assert res["supervisor"] == "Laila"
    assert res["specialist"] == "Moly"
    assert len(res["leads"]) > 0
    assert "Arey Boss! Shob kaj perfectly done!" in res["report_to_boss"]


def test_c2_api_lead_campaign_endpoints():
    client = TestClient(app)

    # 1. Test verify-email endpoint
    v_res = client.post("/api/v1/c2/lead-engine/verify-email", json={"email": "ceo@texaslogistics.com"})
    assert v_res.status_code == 200
    v_data = v_res.json()
    assert v_data["is_safe"] is True
    assert "ReacherHQ" in v_data["verifier"]

    # 2. Test lead campaign endpoint
    c_res = client.post("/api/v1/c2/lead-engine/campaign", json={
        "niche": "Texas Logistics CEOs",
        "criteria": "Managing Directors & Founders",
        "target_sheet_url": "https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
    })
    assert c_res.status_code == 200
    c_data = c_res.json()
    assert c_data["status"] == "COMPLETED"
    assert len(c_data["leads"]) >= 1
    assert "report_to_boss" in c_data


@pytest.mark.asyncio
async def test_c2_executive_desk_lead_intent():
    duo = get_executive_duo()
    prompt = "Laila, Texas logistics sector-er C-Suite decision maker lead lagbe. Moly-ke assign koro."

    res = await duo.process_directive(prompt, operator="Boss")
    tasks = res["tasks"]
    assert len(tasks) >= 2

    moly_task = next((t for t in tasks if t["assignee"] == "Moly"), None)
    laila_task = next((t for t in tasks if t["assignee"] == "Laila"), None)

    assert moly_task is not None
    assert "Moly OSINT Lead Radar" in moly_task["title"]
    assert laila_task is not None
    assert "Laila Lead Supervision" in laila_task["title"]


def test_marketing_squad_lead_chatter_triggers_moly():
    duo = get_executive_duo()
    chat_res = duo.post_group_message(
        group_id="marketing_squad",
        sender="Operator",
        text="Laila, Texas logistics sector-er C-Suite decision maker lead lagbe"
    )
    assert chat_res["success"] is True
    assert chat_res["task_created"] is True

    # Check Laila replied with instant reassurance
    assert "Chill Boss" in chat_res["reply_entry"]["text"]
    assert "Moly" in chat_res["reply_entry"]["text"]

    # Check Moly added backstage telemetry message
    msgs = duo.get_group_messages("marketing_squad")
    moly_msg = next((m for m in msgs if "Moly" in m["sender"]), None)
    assert moly_msg is not None
    assert "4-Tier Waterfall Radar" in moly_msg["text"]
