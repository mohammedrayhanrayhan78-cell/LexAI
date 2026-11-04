from __future__ import annotations

import io
import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
from fastapi.responses import Response
from groq import AsyncGroq

from app.api.deps import get_current_user
from app.models.user import User
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["Voice"])

groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None


@router.post("/transcribe", response_model=dict, status_code=status.HTTP_200_OK)
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    if not groq_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Transcription service (Groq) is not configured.",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No audio file provided.",
        )

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty audio file.",
        )

    try:
        # Wrap audio bytes in an in-memory file-like object with a name attribute for Groq SDK
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = file.filename or "audio.webm"

        transcript = await groq_client.audio.transcriptions.create(
            file=(audio_file.name, audio_file.read()),
            model=settings.GROQ_WHISPER_MODEL,
            response_format="json",
            language="en",
        )

        text = transcript.text if hasattr(transcript, "text") else str(transcript)
        return {"text": text.strip()}
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to transcribe audio.",
        )


@router.post("/synthesize", status_code=status.HTTP_200_OK)
async def synthesize_speech(
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
) -> Response:
    if not settings.ENABLE_TTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Text-to-speech synthesis is disabled.",
        )

    text = payload.get("text")
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text payload is required for synthesis.",
        )

    # Note: Using browser's native Web Speech API synthesis on frontend is recommended when external TTS APIs aren't provisioned.
    # This endpoint acts as a stub / placeholder returning 501 if backend TTS provider is unconfigured.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Backend TTS provider not configured. Use browser native speech synthesis.",
    )