import os
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app
from app.services.voice_service import UnifiedVoiceEngine, voice_engine, AUDIO_CACHE_DIR

client = TestClient(app)


def test_voice_engine_clean_text():
    raw_text = "🌸✨ **Nova PA**: Hii Boss! (｡♥‿♥｡) [Click here](http://example.com) `system` update #Ready! UwU"
    cleaned = voice_engine.clean_text(raw_text)

    # Assert emojis and markers are stripped
    assert "🌸" not in cleaned
    assert "✨" not in cleaned
    assert "UwU" not in cleaned
    assert "**" not in cleaned
    assert "`" not in cleaned
    assert "#" not in cleaned
    assert "Click here" in cleaned
    assert "Hii Boss!" in cleaned


def test_voice_engine_status():
    status = voice_engine.get_status()
    assert status["engine"] == "UnifiedVoiceEngine"
    assert "Nova" in status["personas"]
    assert "Orion" in status["personas"]
    assert "bn-BD-NabanitaNeural" in status["voices"]["Nova"]
    assert "bn-BD-PradeepNeural" in status["voices"]["Orion"]


@pytest.mark.asyncio
async def test_voice_engine_speak_text():
    # Test real synthesis with Edge-TTS
    test_text = "System online. Dual cognitive loop active."
    audio_path = await voice_engine.speak_text(test_text, persona="Nova")

    assert os.path.exists(audio_path)
    file_size = os.path.getsize(audio_path)
    assert file_size > 1000  # Should be a valid mp3 file

    # Cleanup test artifact
    try:
        os.remove(audio_path)
    except Exception:
        pass


def test_router_voice_status():
    res = client.get("/api/v1/voice/status")
    assert res.status_code == 200
    data = res.json()
    assert data["engine"] == "UnifiedVoiceEngine"
    assert "tts_engine" in data


def test_router_speak_endpoint():
    res = client.post("/api/v1/voice/speak", data={"text": "Hello Boss, Orion is ready.", "persona": "Orion"})
    assert res.status_code == 200
    assert res.headers["content-type"] == "audio/mpeg"
    assert len(res.content) > 1000


def test_router_synthesize_endpoint():
    res = client.post("/api/v1/voice/synthesize", json={"text": "Boss, Nova reports all clear!", "persona": "Nova"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "audio_url" in data
    assert data["persona"] == "Nova"

    # Verify fetching the generated audio via get audio endpoint
    audio_res = client.get(data["audio_url"])
    assert audio_res.status_code == 200
    assert audio_res.headers["content-type"] == "audio/mpeg"
    assert len(audio_res.content) > 1000


def test_router_transcribe_endpoint(monkeypatch):
    # Mock voice_engine.transcribe_audio so testing doesn't need a real mic wav
    async def mock_transcribe(audio_path: str) -> str:
        return "Nova, Texas lead hunting update ki?"

    monkeypatch.setattr(voice_engine, "transcribe_audio", mock_transcribe)

    fake_wav_content = b"RIFF....WAVEfmt ...."
    files = {"file": ("mic_test.wav", fake_wav_content, "audio/wav")}
    res = client.post("/api/v1/voice/transcribe", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "Texas lead hunting" in data["transcription"]
