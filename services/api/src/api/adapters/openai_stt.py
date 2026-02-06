"""Speech-to-text adapter using OpenAI gpt-4o-mini-transcribe."""

import logging
from dataclasses import dataclass

from services.api.src.api.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class STTResult:
    text: str
    model: str
    duration_s: float | None = None


def transcribe(audio_bytes: bytes, filename: str = "audio.webm") -> STTResult:
    """Transcribe audio bytes to text.

    If OPENAI_API_KEY is not set, returns a stub response for local dev.
    """
    if not settings.openai_api_key:
        logger.warning("openai_api_key not set, returning stub STT result")
        return STTResult(text="[stub transcript — set OPENAI_API_KEY]", model="stub")

    import openai

    client = openai.OpenAI(api_key=settings.openai_api_key)

    transcription = client.audio.transcriptions.create(
        model=settings.openai_model_stt,
        file=(filename, audio_bytes),
    )

    return STTResult(
        text=transcription.text,
        model=settings.openai_model_stt,
    )
