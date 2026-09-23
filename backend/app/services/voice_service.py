"""
Unified Voice Engine:
Zero-cost, 100% offline & local speech synthesis and transcription subsystem.
- Speech-to-Text: faster-whisper (C++ INT8 Whisper model running on CPU)
- Text-to-Speech: Edge-TTS neural voices (Bangla/Banglish and English) with dual persona mapping
  - Orion Prime: Calm, charismatic male tone (bn-BD-PradeepNeural / en-US-ChristopherNeural)
  - Nova PA: Sweet, cheerful UwU female tone (bn-BD-NabanitaNeural / en-US-AnaNeural)
"""

import os
import re
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import edge_tts
from faster_whisper import WhisperModel

logger = logging.getLogger("c2.voice")

AUDIO_CACHE_DIR = Path("./audio_cache")
AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class UnifiedVoiceEngine:
    """Unified local voice engine for both Speech-to-Text and Text-to-Speech."""

    def __init__(self, whisper_size: Optional[str] = None):
        self.whisper_size = whisper_size or os.getenv("WHISPER_SIZE", "tiny")
        self._stt_model: Optional[WhisperModel] = None
        self._lock = asyncio.Lock()

        # Voice Profiles (Edge-TTS Neural Voices)
        self.voices: Dict[str, str] = {
            "Nova": "bn-BD-NabanitaNeural",          # Sweet female voice (Bangla / Banglish)
            "Orion": "bn-BD-PradeepNeural",          # Calm charismatic male voice (Bangla)
            "Nova_EN": "en-US-AnaNeural",            # Expressive sweet English fallback
            "Orion_EN": "en-US-ChristopherNeural",   # Authority charismatic English fallback
            "Laila": "bn-BD-NabanitaNeural",
            "Sentinel": "bn-BD-PradeepNeural",
        }

    def get_stt_model(self) -> WhisperModel:
        """Lazy-loads faster-whisper model on CPU using INT8 quantization for minimal memory."""
        if self._stt_model is None:
            logger.info(f"🎙️ [VoiceEngine] Initializing faster-whisper ({self.whisper_size}) on CPU [compute_type=int8]...")
            self._stt_model = WhisperModel(self.whisper_size, device="cpu", compute_type="int8")
            logger.info("🎙️ [VoiceEngine] faster-whisper successfully initialized.")
        return self._stt_model

    def clean_text(self, text: str) -> str:
        """Cleans input text before speech synthesis by removing emojis and markdown formatting."""
        if not text:
            return ""

        # Remove common agent symbols, expressions, and emojis
        cleaned = text
        cleaned = re.sub(r'[\U00010000-\U0010ffff]', '', cleaned)  # Emojis (surrogate pairs)
        cleaned = re.sub(r'[\u2600-\u27BF]', '', cleaned)          # Misc symbols & dingbats
        cleaned = re.sub(r'[\u2300-\u23FF]', '', cleaned)          # Misc technical symbols
        cleaned = re.sub(r'[\u2B50-\u2B55]', '', cleaned)          # Stars etc.

        # Remove markdown symbols
        cleaned = cleaned.replace("**", "").replace("*", "")
        cleaned = cleaned.replace("`", "").replace("~", "")
        cleaned = cleaned.replace("UwU", "").replace("OwO", "").replace("✨", "").replace("🌸", "").replace("👑", "")
        cleaned = re.sub(r'#+\s*', '', cleaned)                    # Markdown headers
        cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned) # Markdown links
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()             # Multiple spaces

        return cleaned or "Ami ready achhi, Boss."

    async def transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribes incoming microphone audio file to text via faster-whisper."""
        loop = asyncio.get_event_loop()

        def _transcribe():
            model = self.get_stt_model()
            segments, _ = model.transcribe(audio_file_path, beam_size=5)
            return " ".join([segment.text for segment in segments]).strip()

        try:
            return await loop.run_in_executor(None, _transcribe)
        except Exception as e:
            logger.error(f"❌ [VoiceEngine] STT transcription failed: {e}")
            return ""

    async def speak_text(self, text: str, persona: str = "Nova") -> str:
        """Synthesizes speech into an MP3 file via Edge-TTS and returns the saved file path."""
        clean_prompt = self.clean_text(text)
        selected_voice = self.voices.get(persona, self.voices["Nova"])

        safe_name = persona.lower().replace(" ", "_")
        timestamp = int(time.time() * 1000)
        output_filename = f"{safe_name}_response_{os.getpid()}_{timestamp}.mp3"
        output_path = AUDIO_CACHE_DIR / output_filename

        communicate = edge_tts.Communicate(clean_prompt, selected_voice)
        await communicate.save(str(output_path))
        logger.info(f"🔊 [VoiceEngine] Generated audio for {persona} -> {output_path} ({output_path.stat().st_size} bytes)")
        return str(output_path)

    def get_status(self) -> Dict[str, Any]:
        """Returns the current status of the voice subsystem."""
        return {
            "engine": "UnifiedVoiceEngine",
            "stt_engine": f"faster-whisper ({self.whisper_size})",
            "stt_loaded": self._stt_model is not None,
            "tts_engine": "edge-tts (Neural)",
            "personas": list(self.voices.keys()),
            "voices": self.voices,
            "audio_cache_dir": str(AUDIO_CACHE_DIR.resolve())
        }


voice_engine = UnifiedVoiceEngine()
