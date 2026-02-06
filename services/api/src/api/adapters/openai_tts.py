"""Text-to-speech adapter using OpenAI gpt-4o-mini-tts."""

import base64
import logging
from dataclasses import dataclass

from services.api.src.api.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TTSResult:
    audio_base64: str
    model: str
    content_type: str = "audio/mp3"


def synthesize(text: str, voice: str = "alloy") -> TTSResult:
    """Convert text to speech audio.

    If OPENAI_API_KEY is not set, returns an empty audio stub.
    """
    if not settings.openai_api_key:
        logger.warning("openai_api_key not set, returning empty TTS stub")
        return TTSResult(audio_base64="", model="stub")

    import openai

    client = openai.OpenAI(api_key=settings.openai_api_key)

    response = client.audio.speech.create(
        model=settings.openai_model_tts,
        voice=voice,
        input=text,
    )

    audio_bytes = response.content
    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

    return TTSResult(
        audio_base64=audio_b64,
        model=settings.openai_model_tts,
    )
