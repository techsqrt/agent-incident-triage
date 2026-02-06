"""LLM adapter using OpenAI gpt-4o-mini for schema-driven extraction."""

import json
import logging
from dataclasses import dataclass, field

from services.api.src.api.config import settings
from services.api.src.api.domains.medical.schemas import MedicalExtraction

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResult:
    extraction: MedicalExtraction
    response_text: str
    model: str
    token_usage: dict = field(default_factory=dict)


def extract_medical(
    patient_text: str,
    conversation_history: list[dict] | None = None,
    system_prompt: str = "",
) -> MedicalExtraction:
    """Extract structured medical data from patient text using LLM.

    If OPENAI_API_KEY is not set, falls back to deterministic extraction.
    """
    if not settings.openai_api_key:
        logger.warning("openai_api_key not set, using deterministic extraction")
        from services.api.src.api.routes.triage import _extract_from_text
        return _extract_from_text(patient_text)

    import openai
    from services.api.src.api.domains.medical.prompts import EXTRACTION_SYSTEM_PROMPT

    client = openai.OpenAI(api_key=settings.openai_api_key)

    messages = [{"role": "system", "content": system_prompt or EXTRACTION_SYSTEM_PROMPT}]
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({"role": "user", "content": patient_text})

    response = client.chat.completions.create(
        model=settings.openai_model_text,
        messages=messages,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)

    return MedicalExtraction(**data)


def generate_followup(
    extraction_dict: dict,
    conversation_history: list[dict] | None = None,
    system_prompt: str = "",
) -> tuple[str, dict]:
    """Generate a follow-up question or response based on extraction.

    Returns (response_text, token_usage).
    If OPENAI_API_KEY is not set, returns a stub.
    """
    if not settings.openai_api_key:
        logger.warning("openai_api_key not set, returning stub followup")
        return "[stub response — set OPENAI_API_KEY]", {}

    import openai
    from services.api.src.api.domains.medical.prompts import FOLLOWUP_SYSTEM_PROMPT

    client = openai.OpenAI(api_key=settings.openai_api_key)

    messages = [{"role": "system", "content": system_prompt or FOLLOWUP_SYSTEM_PROMPT}]
    if conversation_history:
        messages.extend(conversation_history)
    messages.append({
        "role": "user",
        "content": f"Current extraction data:\n{json.dumps(extraction_dict, indent=2)}",
    })

    response = client.chat.completions.create(
        model=settings.openai_model_text,
        messages=messages,
    )

    text = response.choices[0].message.content
    usage = {}
    if response.usage:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return text, usage
