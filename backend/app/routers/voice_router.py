"""
FastAPI Voice Router:
Zero-Cost Local Voice Loop Endpoints.
- POST /api/v1/voice/transcribe : Receives audio stream from microphone and returns transcription via faster-whisper.
- POST /api/v1/voice/speak : Synthesizes spoken audio for Orion / Nova via Edge-TTS and returns MP3 FileResponse.
- GET  /api/v1/voice/status : Returns status of STT and TTS engines.
- GET  /api/v1/voice/audio/{filename} : Serves generated audio responses.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.services.voice_service import voice_engine, AUDIO_CACHE_DIR

logger = logging.getLogger("c2.voice_router")

router = APIRouter(prefix="/api/v1/voice", tags=["Voice Engine"])


class SynthesizeRequest(BaseModel):
    text: str
    persona: Optional[str] = "Nova"


@router.get("/status")
def get_voice_status():
    """Returns the operational status of the Voice Engine."""
    return voice_engine.get_status()


@router.post("/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)):
    """Receives recorded audio from the browser, transcribes it with faster-whisper, and returns text."""
    safe_filename = file.filename or "mic_input.wav"
    temp_path = AUDIO_CACHE_DIR / f"temp_input_{os.getpid()}_{safe_filename}"

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        transcription = await voice_engine.transcribe_audio(str(temp_path))
        return {
            "status": "success",
            "transcription": transcription
        }
    except Exception as e:
        logger.error(f"Error in voice transcription: {e}")
        raise HTTPException(status_code=500, detail=f"Voice transcription failed: {str(e)}")
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception as e:
                logger.warning(f"Could not delete temp audio file {temp_path}: {e}")


@router.post("/speak")
async def speak_endpoint(
    text: str = Form(...),
    persona: str = Form("Nova")
):
    """Synthesizes speech from form data and streams the MP3 audio file back."""
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    try:
        audio_path = await voice_engine.speak_text(text, persona=persona)
        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            filename=Path(audio_path).name
        )
    except Exception as e:
        logger.error(f"Error synthesizing speech for {persona}: {e}")
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")


@router.post("/synthesize")
async def synthesize_json_endpoint(req: SynthesizeRequest = Body(...)):
    """JSON-based endpoint to synthesize speech, returning the audio URL and file metadata."""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    try:
        audio_path = await voice_engine.speak_text(req.text, persona=req.persona or "Nova")
        filename = Path(audio_path).name
        return {
            "status": "success",
            "persona": req.persona or "Nova",
            "audio_url": f"/api/v1/voice/audio/{filename}",
            "filename": filename,
            "text": req.text
        }
    except Exception as e:
        logger.error(f"Error in json speech synthesis: {e}")
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")


@router.get("/audio/{filename}")
async def get_audio_file(filename: str):
    """Streams a generated audio response from the local cache."""
    # Prevent directory traversal
    safe_name = os.path.basename(filename)
    audio_file = AUDIO_CACHE_DIR / safe_name

    if not audio_file.exists():
        raise HTTPException(status_code=404, detail="Audio file not found or expired.")

    return FileResponse(
        str(audio_file),
        media_type="audio/mpeg",
        filename=safe_name
    )
