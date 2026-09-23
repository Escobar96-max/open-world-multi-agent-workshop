import sys
from pathlib import Path
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.executive_duo import ExecutiveDuo, sanitize_banglish_text, is_gibberish_or_hallucination

@pytest.fixture
def duo():
    return ExecutiveDuo(ollama_enabled=False)

def test_sanitize_banglish_text():
    # Test typo correction
    raw = "Boss, ami apnake valovasi! upodate ashche kina thik thak dekce?"
    cleaned = sanitize_banglish_text(raw)
    assert "valobashi" in cleaned
    assert "update" in cleaned
    assert "thikthak" in cleaned
    assert "dekheche" in cleaned

    # Test corrupted unicode removal
    corrupted = "Hii Boss! UwU ³§ 🌸✨"
    cleaned = sanitize_banglish_text(corrupted)
    assert "³" not in cleaned
    assert "§" not in cleaned
    assert "UwU" in cleaned

    # Test hallucination removal
    hallu = "Chill Boss! Architect_Prime koto ase. Borsho Architect_Prime. Choto koto, shob check maaf koto update ki?"
    cleaned = sanitize_banglish_text(hallu)
    assert "Borsho" not in cleaned
    assert "choto koto" not in cleaned
    assert "maaf koto" not in cleaned

def test_is_gibberish_or_hallucination():
    assert is_gibberish_or_hallucination("Borsho Architect_Prime: Work Plaza") is True
    assert is_gibberish_or_hallucination("Choto koto, shob check maaf koto update ki?") is True
    assert is_gibberish_or_hallucination("Aapdaatmak parivartan ke baare mein") is True
    assert is_gibberish_or_hallucination("Hii Boss! UwU ³§ 🌸✨") is True
    assert is_gibberish_or_hallucination("Arey Boss! Ami ekdom bindas achi! Apnar ki obostha?") is False

@pytest.mark.asyncio
async def test_world_query_grounding(duo):
    res = await duo.process_directive("okhane agents der ki obostha ? tader world er vetore environment er updates ki?")
    orion = res["orion_response"]
    nova = res["nova_response"]

    # Verify no hallucinations
    for text in [orion, nova]:
        assert "Borsho" not in text
        assert "choto koto" not in text
        assert "maaf koto" not in text
        assert "³" not in text
        assert "§" not in text

    # Verify real grounding
    assert "Architect_Prime" in orion or "Architect_Prime" in nova
    assert "432Hz" in orion or "432Hz" in nova
    assert "Work Plaza" in orion or "Work Plaza" in nova

@pytest.mark.asyncio
async def test_frustration_and_stress_handling(duo):
    res = await duo.process_directive("matha kharap hoye jacche")
    orion = res["orion_response"]
    nova = res["nova_response"]

    assert any(w in orion.lower() for w in ["calm", "thanda", "pera", "relax", "chill"])
    assert any(w in nova.lower() for w in ["pera", "rest", "tension", "pani", "uwu"])

@pytest.mark.asyncio
async def test_spelling_and_language_feedback(duo):
    res = await duo.process_directive("onek beshi spelling mistakes and bhul words use korche")
    orion = res["orion_response"]
    nova = res["nova_response"]

    assert any(w in orion.lower() for w in ["model", "banglish", "clean", "filter", "hindi"])
    assert any(w in nova.lower() for w in ["model", "filter", "banglish", "spelling", "clean"])
