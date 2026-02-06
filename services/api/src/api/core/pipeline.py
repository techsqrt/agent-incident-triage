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
    stt_result = stt_fn(audio_bytes, filename)
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
    extraction = extract_fn(stt_result.text)
    extract_ms = int((time.monotonic() - t0) * 1000)

    result.extraction = extraction

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="EXTRACT",
        payload_json=redact_dict(extraction.model_dump()),
        latency_ms=extract_ms,
        model_used="deterministic",
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
    response_text, token_usage = generate_fn(
        extraction.model_dump(),
    )
    gen_ms = int((time.monotonic() - t0) * 1000)

    result.response_text = response_text
    msg_repo.create(incident_id, "assistant", response_text)

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="GENERATE",
        payload_json={"disposition": assessment.disposition},
        latency_ms=gen_ms,
        model_used="deterministic",
        token_usage_json=token_usage if token_usage else None,
    )

    # --------------- Step 5: TTS ---------------
    t0 = time.monotonic()
    tts_result = tts_fn(response_text)
    tts_ms = int((time.monotonic() - t0) * 1000)

    result.audio_base64 = tts_result.audio_base64 or None

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="TTS",
        payload_json={"audio_length": len(tts_result.audio_base64) if tts_result.audio_base64 else 0},
        latency_ms=tts_ms,
        model_used=tts_result.model,
    )

    logger.info("pipeline_complete", extra={
        "incident_id": incident_id,
        "trace_id": trace_id,
        "acuity": assessment.acuity,
        "total_ms": stt_ms + extract_ms + rules_ms + gen_ms + tts_ms,
    })

    return result
