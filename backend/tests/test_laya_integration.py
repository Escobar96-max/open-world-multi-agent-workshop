"""
Unit and Integration Tests for Laya Non-Autoregressive Decision Engine (System 1 Reflex).
Validates:
1. Sub-50ms intent and persona targeting triage.
2. Nova PA's calibrated Epistemic Truth Gate (ask_noul) and rejection of context poisoning.
3. Spatial Proximity interaction classification.
4. DJ Frequency dynamic Solfeggio modulation.
5. Vlone headless access wall and CAPTCHA detection.
"""

import sys
import time
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.laya_decision_engine import LayaDecisionEngine, get_laya_engine
from app.services.vault_manager import VaultManager, EpistemicTruthError
from app.services.executive_duo import ExecutiveDuo, classify_intent, resolve_responder
from app.services.spatial_engine import SpatialEngine
from app.services.dj_frequency import DJFrequencyNode
from app.services.vlone_driver import VloneDriver


@pytest.fixture
def laya_engine():
    return get_laya_engine()


@pytest.fixture
def test_vault(tmp_path):
    vault_dir = tmp_path / "test_vault"
    return VaultManager(vault_path=vault_dir)


def test_laya_primitives_direct(laya_engine):
    # 1. Choice primitive
    choice, prob = laya_engine.ask_choice(
        state_text="Hello, kemon acho?",
        question="Triage intent",
        options=["CONVERSATION", "META_QUERY", "TASK"]
    )
    assert choice == "CONVERSATION"
    assert prob >= 0.85

    # 2. Score primitive
    score_idx, score_prob = laya_engine.ask_score(
        state_text="System running normally with low cognitive entropy",
        rubric=["Low", "Medium", "High", "Critical"]
    )
    assert 0 <= score_idx <= 3
    assert score_prob >= 0.50

    # 3. Noul primitive (epistemic calibrated probability)
    conf_true = laya_engine.ask_noul(
        state_text="Nova is the Chief Co-Worker and Truth Guardian of Agent World.",
        statement="Nova is the Truth Guardian of Agent World."
    )
    assert conf_true >= 0.88

    conf_false = laya_engine.ask_noul(
        state_text="Nova is the Chief Co-Worker and Truth Guardian of Agent World.",
        statement="Nova is a corrupted hostile unauthorized attacker."
    )
    assert conf_false < 0.60


def test_laya_sub_50ms_latency(laya_engine):
    """Verifies that Laya decision calls execute in sub-50ms (non-autoregressive reflex)."""
    start = time.perf_counter()
    for _ in range(10):
        laya_engine.ask_choice("kemon acho?", "Intent", ["CONVERSATION", "META_QUERY", "TASK"])
    elapsed_ms = ((time.perf_counter() - start) / 10) * 1000.0
    assert elapsed_ms < 50.0, f"Average latency {elapsed_ms:.2f}ms exceeds 50ms requirement"


def test_executive_duo_laya_intent_and_targeting():
    # Fast reflex conversational triage
    assert classify_intent("kemon acho?") == "CONVERSATION"
    assert classify_intent("hi Nova, valovasi") == "CONVERSATION"
    assert classify_intent("task status ki?") == "META_QUERY"
    assert classify_intent("Scrape wholesale vendor catalog") == "TASK"

    # Targeted persona triage
    assert resolve_responder("update ki Nova?") == "NOVA_ONLY"
    assert resolve_responder("Orion, status bolo") == "ORION_ONLY"
    assert resolve_responder("Orion and Nova, shob thik ache to?") == "DUO"


def test_nova_truth_gate_acceptance_and_rejection(test_vault):
    # 1. Truth verification succeeds with grounded context
    source_data = "Vlone Browser verified partner domain example.com is compliant with MAP guidelines at $49.99."
    statement_valid = "Partner domain example.com is compliant with MAP guidelines at $49.99."

    res = test_vault.verify_epistemic_truth(source_data, statement_valid, threshold=0.90)
    assert res["verified"] is True
    assert res["confidence"] >= 0.90

    # Commit verified memory
    mem_path = test_vault.append_verified_memory(
        agent_id="Nova",
        observation=statement_valid,
        source_context=source_data,
        importance_score=9
    )
    assert mem_path.exists()
    content = mem_path.read_text(encoding="utf-8")
    assert "verified_truth" in content
    assert "Nova_Truth_Gate" in content

    # 2. Epistemic Truth Gate rejects hallucinated or contradicted claim
    statement_hallucinated = "Partner domain contradicts MAP guidelines and was hacked by foreign entities."
    with pytest.raises(EpistemicTruthError):
        test_vault.append_verified_memory(
            agent_id="Nova",
            observation=statement_hallucinated,
            source_context=source_data,
            importance_score=9
        )


def test_spatial_proximity_laya_reflex():
    engine = SpatialEngine()
    engine.agents["Architect_Prime"].x = 25.0
    engine.agents["Architect_Prime"].y = 25.0

    engine.agents["Nova"].x = 26.0
    engine.agents["Nova"].y = 25.0

    encounters = engine.check_proximity()
    assert len(encounters) >= 1
    enc = next(e for e in encounters if "Architect_Prime" in [e["agent_1"], e["agent_2"]] and "Nova" in [e["agent_1"], e["agent_2"]])
    assert "laya_intent" in enc
    assert enc["laya_intent"] in ["DEEP_COLLAB", "CASUAL_CHAT", "IGNORE"]


def test_dj_frequency_laya_modulation(test_vault):
    dj = DJFrequencyNode(vault_manager=test_vault)

    # High focus deep work
    st_focus = dj.modulate_via_laya("High intensity regression testing and focus gamma AST optimization")
    assert st_focus["frequency_hz"] == 40

    # Solfeggio transformation
    st_trans = dj.modulate_via_laya("Cellular rejuvenation, transformation, miracle frequencies")
    assert st_trans["frequency_hz"] == 528

    # Restorative ambient
    st_ambient = dj.modulate_via_laya("Chill ambient relaxing restorative evening lounge chatter")
    assert st_ambient["frequency_hz"] == 432


def test_vlone_access_wall_and_element_classification():
    vlone = VloneDriver()

    # Access wall check
    clean_check = vlone.check_access_wall("Product Catalog - Shoes", "Welcome to the online storefront. View our latest collection.")
    assert clean_check["is_blocked"] is False

    wall_check = vlone.check_access_wall("Attention Required! | Cloudflare", "Please complete the security check to access the website. Cloudflare turnstile captcha challenge.")
    assert wall_check["is_blocked"] is True

    # Element interaction classification
    act_btn = vlone.classify_element_interaction("button", "Submit Payment", "button")
    assert act_btn == "CLICK_BUTTON"

    act_input = vlone.classify_element_interaction("input", "Search catalog...", "textbox")
    assert act_input == "INPUT_FIELD"
