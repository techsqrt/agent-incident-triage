"""Medical voice pipeline runner.

Orchestrates: STT → Extract → Rules → Generate → TTS
Each step is logged to audit_events with trace_id, latency, and redacted payloads.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field

from services.api.src.api.core.redaction import redact_dict
from services.api.src.api.db.repository import (
    AssessmentRepository,
    AuditEventRepository,
    IncidentRepository,
    MessageRepository,
)
from services.api.src.api.domains.medical.rules import assess
from services.api.src.api.domains.medical.schemas import MedicalExtraction

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of the full voice pipeline."""

    transcript: str = ""
    extraction: MedicalExtraction | None = None
    response_text: str = ""
    audio_base64: str | None = None
    assessment_row: dict | None = None
    trace_id: str = ""
    error: str | None = None


def run_voice_pipeline(
    incident_id: str,
    audio_bytes: bytes,
    filename: str,
    engine,
    *,
    stt_fn=None,
    extract_fn=None,
    generate_fn=None,
    tts_fn=None,
) -> PipelineResult:
    """Run the full voice pipeline for a medical triage incident.

    Adapter functions are injectable for testing. When None, uses real adapters.
    Each step is wrapped in error handling — failures log a STEP_FAILED audit
    event and return a partial result rather than crashing.
    """
    from services.api.src.api.adapters.openai_stt import transcribe as default_stt
    from services.api.src.api.adapters.openai_llm import (
        extract_medical as default_extract,
        generate_followup as default_generate,
    )
    from services.api.src.api.adapters.openai_tts import synthesize as default_tts

    stt_fn = stt_fn or default_stt
    extract_fn = extract_fn or default_extract
    generate_fn = generate_fn or default_generate
    tts_fn = tts_fn or default_tts

    trace_id = str(uuid.uuid4())
    incident_repo = IncidentRepository(engine)
    msg_repo = MessageRepository(engine)
    assess_repo = AssessmentRepository(engine)
    audit_repo = AuditEventRepository(engine)

    incident = incident_repo.get(incident_id)
    result = PipelineResult(trace_id=trace_id)

    # --------------- Step 1: STT ---------------
    t0 = time.monotonic()
    try:
        stt_result = stt_fn(audio_bytes, filename)
    except Exception as exc:
        stt_ms = int((time.monotonic() - t0) * 1000)
        logger.error("pipeline_stt_failed", extra={
            "incident_id": incident_id, "trace_id": trace_id, "error": str(exc),
        })
        audit_repo.append(
            incident_id=incident_id, trace_id=trace_id, step="STT_FAILED",
            payload_json={"error": str(exc)}, latency_ms=stt_ms,
        )
        result.error = f"STT failed: {exc}"
        return result
    stt_ms = int((time.monotonic() - t0) * 1000)

    result.transcript = stt_result.text
    msg_repo.create(incident_id, "patient", stt_result.text)

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="STT",
        payload_json={"transcript_length": len(stt_result.text)},
        latency_ms=stt_ms,
        model_used=stt_result.model,
    )

    logger.info("pipeline_stt", extra={
        "incident_id": incident_id, "trace_id": trace_id, "latency_ms": stt_ms,
    })

    # --------------- Step 2: Extract ---------------
    t0 = time.monotonic()
    try:
        extraction = extract_fn(stt_result.text)
    except Exception as exc:
        extract_ms = int((time.monotonic() - t0) * 1000)
        logger.error("pipeline_extract_failed", extra={
            "incident_id": incident_id, "trace_id": trace_id, "error": str(exc),
        })
        audit_repo.append(
            incident_id=incident_id, trace_id=trace_id, step="EXTRACT_FAILED",
            payload_json={"error": str(exc)}, latency_ms=extract_ms,
        )
        # Fall back to deterministic extraction
        from services.api.src.api.domains.medical.extract import extract_from_text
        extraction = extract_from_text(stt_result.text)
    extract_ms = int((time.monotonic() - t0) * 1000)

    result.extraction = extraction

    # Determine which model was actually used
    extract_model = "deterministic"
    from services.api.src.api.config import settings
    if settings.openai_api_key:
        extract_model = settings.openai_model_text

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="EXTRACT",
        payload_json=redact_dict(extraction.model_dump()),
        latency_ms=extract_ms,
        model_used=extract_model,
    )

    # --------------- Step 3: Triage Rules ---------------
    t0 = time.monotonic()
    assessment = assess(extraction)
    rules_ms = int((time.monotonic() - t0) * 1000)

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="TRIAGE_RULES",
        payload_json={"acuity": assessment.acuity, "escalate": assessment.escalate},
        latency_ms=rules_ms,
    )

    # Persist assessment
    assessment_row = assess_repo.create(
        incident_id=incident_id,
        domain=incident["domain"],
        result_json=assessment.model_dump(),
    )
    result.assessment_row = assessment_row

    # Update incident status if escalation needed
    if assessment.escalate:
        incident_repo.update_status(incident_id, "ESCALATED")

    # --------------- Step 4: Generate Response ---------------
    t0 = time.monotonic()
    try:
        response_text, token_usage = generate_fn(extraction.model_dump())
    except Exception as exc:
        gen_ms = int((time.monotonic() - t0) * 1000)
        logger.error("pipeline_generate_failed", extra={
            "incident_id": incident_id, "trace_id": trace_id, "error": str(exc),
        })
        audit_repo.append(
            incident_id=incident_id, trace_id=trace_id, step="GENERATE_FAILED",
            payload_json={"error": str(exc)}, latency_ms=gen_ms,
        )
        response_text = "I'm having trouble generating a response. Please try again."
        token_usage = {}
    gen_ms = int((time.monotonic() - t0) * 1000)

    result.response_text = response_text
    msg_repo.create(incident_id, "assistant", response_text)

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="GENERATE",
        payload_json={"disposition": assessment.disposition},
        latency_ms=gen_ms,
        model_used=extract_model,
        token_usage_json=token_usage if token_usage else None,
    )

    # --------------- Step 5: TTS ---------------
    t0 = time.monotonic()
    try:
        tts_result = tts_fn(response_text)
        result.audio_base64 = tts_result.audio_base64 or None
        tts_model = tts_result.model
    except Exception as exc:
        logger.error("pipeline_tts_failed", extra={
            "incident_id": incident_id, "trace_id": trace_id, "error": str(exc),
        })
        tts_model = "failed"
        result.audio_base64 = None
    tts_ms = int((time.monotonic() - t0) * 1000)

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="TTS",
        payload_json={"audio_length": len(result.audio_base64) if result.audio_base64 else 0},
        latency_ms=tts_ms,
        model_used=tts_model,
    )

    logger.info("pipeline_complete", extra={
        "incident_id": incident_id,
        "trace_id": trace_id,
        "acuity": assessment.acuity,
        "total_ms": stt_ms + extract_ms + rules_ms + gen_ms + tts_ms,
    })

    return result
