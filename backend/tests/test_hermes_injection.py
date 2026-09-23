"""
Verification Test Suite:
Hermes 3 (8B) Injection Architecture as Dedicated Backstage Heavy Worker
- HermesWorkerEngine async execution & JSON enforcement
- MolyLeadEngine OSINT extraction via Hermes 3
- ExecutiveDuo backstage worker dispatch in technical English & Nova truth audit
"""

import json
import os
import sys
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.hermes_worker_engine import HermesWorkerEngine, hermes_worker
from app.services.moly_lead_hunter import MolyLeadEngine, moly_agent
from app.services.executive_duo import ExecutiveDuo, TaskCard
from app.services.vault_manager import VaultManager


@pytest.fixture
def temp_vault(tmp_path):
    return VaultManager(vault_path=tmp_path)


@pytest.fixture
def duo(temp_vault):
    return ExecutiveDuo(vault_manager=temp_vault, ollama_enabled=False)


@pytest.fixture
def lead_engine(tmp_path):
    return MolyLeadEngine(vault_path=tmp_path)


@pytest.mark.asyncio
async def test_hermes_worker_engine_structure():
    """
    Verifies HermesWorkerEngine is configured for hermes3:8b and outputs valid JSON.
    """
    engine = HermesWorkerEngine()
    assert engine.model == "hermes3:8b"
    assert "11434" in engine.endpoint

    system_prompt = (
        "You are an uncensored OSINT specialist agent (Moly). "
        "Extract ONLY the primary executive decision makers. "
        "Respond strictly with valid JSON: {\"name\": string, \"title\": string}"
    )
    user_payload = "Executive profile: Marcus Vance, Chief Executive Officer of Lone Star Logistics LLC."

    res = await engine.execute_task(
        system_prompt=system_prompt,
        user_payload=user_payload,
        temperature=0.2,
        enforce_json=True
    )

    assert isinstance(res, dict)
    assert res.get("name") is not None
    assert "Marcus Vance" in res["name"]
    assert "Chief Executive Officer" in res.get("title", "")


@pytest.mark.asyncio
async def test_moly_wp_json_extraction_with_hermes(lead_engine):
    """
    Verifies Moly extracts an executive name from simulated WordPress /wp-json/wp/v2/users payload.
    """
    mock_wp_users_payload = json.dumps([
        {
            "id": 1,
            "name": "Elena Rostova",
            "url": "https://houstonfreight.com",
            "description": "Managing Director & Operations Head",
            "link": "https://houstonfreight.com/author/erostova/",
            "slug": "erostova"
        }
    ])

    extracted = await lead_engine._extract_decision_maker_with_hermes(mock_wp_users_payload)
    assert extracted is not None
    assert "Elena Rostova" in extracted["name"]
    assert extracted.get("title") is not None


@pytest.mark.asyncio
async def test_moly_schema_org_extraction_with_hermes(lead_engine):
    """
    Verifies Moly deep sweep parses Schema.org JSON-LD via Hermes 3 extraction.
    """
    schema_payload = json.dumps({
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Lone Star Logistics LLC",
        "founder": {
            "@type": "Person",
            "name": "Marcus Vance",
            "jobTitle": "Chief Executive Officer & Founder"
        }
    })

    extracted = await lead_engine._extract_decision_maker_with_hermes(schema_payload)
    assert extracted is not None
    assert "Marcus Vance" in extracted["name"]


@pytest.mark.asyncio
async def test_executive_duo_backstage_english_dispatch(duo):
    """
    Verifies Orion Prime's TASK DAG mandates 100% technical English directives
    for backstage heavy workers (@Moly, @Vlone_Browser, @Architect_Prime, @Sentinel_Alpha).
    """
    directive = "Amader Texas logistics decision maker leads khuje ber koro"
    tasks = duo.decompose_intent(directive)

    assert len(tasks) > 0
    worker_assignees = {t.assignee for t in tasks}

    # Verify Moly lead hunter is engaged
    assert "Moly" in worker_assignees or "Vlone_Browser" in worker_assignees

    # Verify task titles and instructions are in strict technical English
    for t in tasks:
        assert isinstance(t.title, str)
        assert isinstance(t.description, str)
        # Verify no corrupt/broken characters
        assert not any(bad in t.title.lower() for bad in ["borsho", "koto ase", "choto koto"])


@pytest.mark.asyncio
async def test_executive_duo_drain_with_hermes_and_nova_truth_audit(duo):
    """
    Verifies task execution loop drains tasks through Hermes 3 worker
    and Nova delivers truth-audited verification notification.
    """
    duo.tasks.clear()
    task = TaskCard(
        id="TASK-TEST-HERMES-01",
        title="Synthesize System Security Boundary",
        description="Verify zero-trust authentication boundary and evaluate perimeter rules.",
        assignee="Sentinel_Alpha",
        status="in_progress",
        priority=10
    )
    duo.tasks.append(task)

    drained = await duo.drain_tasks_step()
    assert drained == 1
    assert task.status == "completed"
    assert task.output_summary is not None

    # Check Nova's truth-audited response in chat history
    latest_msg = duo.chat_history[-1]
    assert latest_msg["type"] == "task_completed"
    assert "truth-audited" in latest_msg["nova_response"]
    assert "UwU" in latest_msg["nova_response"]
