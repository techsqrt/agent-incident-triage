"""Triage API endpoints."""

import logging
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.engine import Engine

from services.api.src.api.config import settings
from services.api.src.api.core.feature_flags import ALL_DOMAINS, is_domain_active
from services.api.src.api.core.redaction import redact_dict
from services.api.src.api.db.engine import get_engine
from services.api.src.api.db.repository import (
    AssessmentRepository,
    AuditEventRepository,
    IncidentRepository,
    MessageRepository,
    VerifiedIPRepository,
)
from services.api.src.api.domains.medical.extract import extract_from_text
from services.api.src.api.domains.medical.rules import assess
from services.api.src.api.domains.medical.schemas import MedicalExtraction
from datetime import datetime
from services.api.src.api.schemas.enums import Domain, IncidentMode, IncidentStatus, Severity

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB

# Map ESI acuity levels to severity enum
ACUITY_TO_SEVERITY = {
    1: Severity.ESI_1,
    2: Severity.ESI_2,
    3: Severity.ESI_3,
    4: Severity.ESI_4,
    5: Severity.ESI_5,
}

from services.api.src.api.schemas.responses import (
    AssessmentResponse,
    AuditEventResponse,
    CreateIncidentRequest,
    IncidentListResponse,
    IncidentResponse,
    MessageResponse,
    MessageWithAssessmentResponse,
    SendMessageRequest,
    TimelineResponse,
    UpdateIncidentStatusRequest,
    VoiceResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_client_ip(request: Request) -> str:
    """Get client IP from request, handling proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _verify_recaptcha(token: str | None, request: Request, engine: Engine) -> None:
    """Verify reCAPTCHA token if secret key is configured. Caches verified IPs for 7 days."""
    recaptcha_secret = settings.recaptcha_secret_key
    if not recaptcha_secret:
        return

    client_ip = _get_client_ip(request)
    ip_repo = VerifiedIPRepository(engine)

    if ip_repo.is_verified(client_ip):
        logger.info("recaptcha_ip_cached", extra={"ip": client_ip})
        return

    if not token:
        raise HTTPException(403, "reCAPTCHA token required")

    import httpx
    resp = httpx.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data={"secret": recaptcha_secret, "response": token},
    )
    result = resp.json()
    logger.info("recaptcha_google_response", extra={"ip": client_ip, "result": result})

    if not result.get("success"):
        error_codes = result.get("error-codes", [])
        logger.warning("recaptcha_verification_failed", extra={"ip": client_ip, "errors": error_codes})
        raise HTTPException(403, f"reCAPTCHA verification failed: {error_codes}")

    ip_repo.add(client_ip)
    logger.info("recaptcha_ip_verified", extra={"ip": client_ip})


def _engine() -> Engine:
    return get_engine()


def _str_dt(dt) -> str:
    """Convert a datetime to ISO string."""
    return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)


# ---------------------------------------------------------------------------
# reCAPTCHA IP verification status
# ---------------------------------------------------------------------------

@router.get("/recaptcha/status")
def check_recaptcha_status(
    request: Request,
    engine: Engine = Depends(_engine),
) -> dict:
    """Check if client IP is already verified (cached for 7 days)."""
    recaptcha_secret = settings.recaptcha_secret_key
    if not recaptcha_secret:
        logger.info("recaptcha_status_no_secret")
        return {"verified": True, "required": False}

    client_ip = _get_client_ip(request)
    ip_repo = VerifiedIPRepository(engine)
    is_verified = ip_repo.is_verified(client_ip)
    logger.info("recaptcha_status_check", extra={"ip": client_ip, "verified": is_verified})

    return {"verified": is_verified, "required": True}


# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------

@router.get("/domains")
def list_domains() -> dict:
    """List all domains and their active status."""
    domains = []
    for domain in ALL_DOMAINS:
        domains.append({
            "name": domain,
            "active": is_domain_active(domain),
        })
    return {"domains": domains}


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

@router.post("/incidents", response_model=IncidentResponse)
def create_incident(
    body: CreateIncidentRequest,
    engine: Engine = Depends(_engine),
) -> IncidentResponse:
    """Create a new triage incident."""
    domain_str = body.domain.value if isinstance(body.domain, Domain) else body.domain
    mode_str = body.mode.value if isinstance(body.mode, IncidentMode) else body.mode

    if domain_str not in ALL_DOMAINS:
        raise HTTPException(400, f"Unknown domain: {domain_str}")
    if not is_domain_active(domain_str):
        raise HTTPException(400, f"Domain '{domain_str}' is not active")

    repo = IncidentRepository(engine)
    row = repo.create(domain=domain_str, mode=mode_str)

    logger.info("incident_created", extra={"incident_id": row["id"], "domain": domain_str})

    return IncidentResponse(
        id=row["id"],
        domain=row["domain"],
        status=row["status"],
        mode=row["mode"],
        severity=row.get("severity", "UNASSIGNED"),
        created_at=_str_dt(row["created_at"]),
        updated_at=_str_dt(row["updated_at"]),
    )


@router.get("/incidents", response_model=IncidentListResponse)
def list_incidents(
    domain: Domain | None = Query(None),
    status: IncidentStatus | None = Query(None),
    severity: Severity | None = Query(None),
    updated_after: datetime | None = Query(None, description="Filter by updated_at >= this datetime (ISO format)"),
    updated_before: datetime | None = Query(None, description="Filter by updated_at <= this datetime (ISO format)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    engine: Engine = Depends(_engine),
) -> IncidentListResponse:
    """List incidents with optional filters."""
    repo = IncidentRepository(engine)

    domain_str = domain.value if domain else None
    status_str = status.value if status else None
    severity_str = severity.value if severity else None

    rows = repo.list_all(
        domain=domain_str,
        status=status_str,
        severity=severity_str,
        updated_after=updated_after,
        updated_before=updated_before,
        limit=limit,
        offset=offset,
    )
    total = repo.count_all(
        domain=domain_str,
        status=status_str,
        severity=severity_str,
        updated_after=updated_after,
        updated_before=updated_before,
    )

    return IncidentListResponse(
        incidents=[
            IncidentResponse(
                id=row["id"],
                domain=row["domain"],
                status=row["status"],
                mode=row["mode"],
                severity=row.get("severity", "UNASSIGNED"),
                created_at=_str_dt(row["created_at"]),
                updated_at=_str_dt(row["updated_at"]),
            )
            for row in rows
        ],
        total=total,
    )


@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: str,
    engine: Engine = Depends(_engine),
) -> IncidentResponse:
    """Get a triage incident by ID."""
    repo = IncidentRepository(engine)
    row = repo.get(incident_id)
    if not row:
        raise HTTPException(404, "Incident not found")

    return IncidentResponse(
        id=row["id"],
        domain=row["domain"],
        status=row["status"],
        mode=row["mode"],
        severity=row.get("severity", "UNASSIGNED"),
        created_at=_str_dt(row["created_at"]),
        updated_at=_str_dt(row["updated_at"]),
        history=row.get("history"),
    )


@router.patch("/incidents/{incident_id}/status", response_model=IncidentResponse)
def update_incident_status(
    incident_id: str,
    body: UpdateIncidentStatusRequest,
    engine: Engine = Depends(_engine),
) -> IncidentResponse:
    """Update incident status (close, reopen, etc.)."""
    repo = IncidentRepository(engine)
    row = repo.get(incident_id)
    if not row:
        raise HTTPException(404, "Incident not found")

    current_status = IncidentStatus(row["status"])
    new_status = body.status

    # Validate status transitions
    valid_transitions = {
        IncidentStatus.OPEN: [IncidentStatus.TRIAGE_READY, IncidentStatus.ESCALATED, IncidentStatus.CLOSED],
        IncidentStatus.TRIAGE_READY: [IncidentStatus.ESCALATED, IncidentStatus.CLOSED],
        IncidentStatus.ESCALATED: [IncidentStatus.CLOSED],
        IncidentStatus.CLOSED: [IncidentStatus.OPEN],  # reopen
    }

    if new_status not in valid_transitions.get(current_status, []):
        raise HTTPException(
            400,
            f"Invalid status transition: {current_status.value} -> {new_status.value}"
        )

    repo.update_status(incident_id, new_status.value)

    # Add interaction to history
    repo.append_interaction(incident_id, {
        "type": f"status_changed_to_{new_status.value.lower()}",
        "ts": _str_dt(repo.get(incident_id)["updated_at"]),
        "from_status": current_status.value,
        "to_status": new_status.value,
    })

    updated = repo.get(incident_id)
    logger.info("incident_status_updated", extra={
        "incident_id": incident_id,
        "from": current_status.value,
        "to": new_status.value,
    })

    return IncidentResponse(
        id=updated["id"],
        domain=updated["domain"],
        status=updated["status"],
        mode=updated["mode"],
        severity=updated.get("severity", "UNASSIGNED"),
        created_at=_str_dt(updated["created_at"]),
        updated_at=_str_dt(updated["updated_at"]),
    )


@router.post("/incidents/{incident_id}/close", response_model=IncidentResponse)
def close_incident(
    incident_id: str,
    engine: Engine = Depends(_engine),
) -> IncidentResponse:
    """Close an incident."""
    repo = IncidentRepository(engine)
    row = repo.get(incident_id)
    if not row:
        raise HTTPException(404, "Incident not found")

    if row["status"] == IncidentStatus.CLOSED.value:
        raise HTTPException(400, "Incident is already closed")

    repo.update_status(incident_id, IncidentStatus.CLOSED.value)
    repo.append_interaction(incident_id, {
        "type": "incident_closed",
        "ts": _str_dt(repo.get(incident_id)["updated_at"]),
        "from_status": row["status"],
    })

    updated = repo.get(incident_id)
    logger.info("incident_closed", extra={"incident_id": incident_id})

    return IncidentResponse(
        id=updated["id"],
        domain=updated["domain"],
        status=updated["status"],
        mode=updated["mode"],
        severity=updated.get("severity", "UNASSIGNED"),
        created_at=_str_dt(updated["created_at"]),
        updated_at=_str_dt(updated["updated_at"]),
    )


@router.post("/incidents/{incident_id}/reopen", response_model=IncidentResponse)
def reopen_incident(
    incident_id: str,
    engine: Engine = Depends(_engine),
) -> IncidentResponse:
    """Reopen a closed incident."""
    repo = IncidentRepository(engine)
    row = repo.get(incident_id)
    if not row:
        raise HTTPException(404, "Incident not found")

    if row["status"] != IncidentStatus.CLOSED.value:
        raise HTTPException(400, "Only closed incidents can be reopened")

    repo.update_status(incident_id, IncidentStatus.OPEN.value)
    repo.append_interaction(incident_id, {
        "type": "incident_reopened",
        "ts": _str_dt(repo.get(incident_id)["updated_at"]),
    })

    updated = repo.get(incident_id)
    logger.info("incident_reopened", extra={"incident_id": incident_id})

    return IncidentResponse(
        id=updated["id"],
        domain=updated["domain"],
        status=updated["status"],
        mode=updated["mode"],
        severity=updated.get("severity", "UNASSIGNED"),
        created_at=_str_dt(updated["created_at"]),
        updated_at=_str_dt(updated["updated_at"]),
    )


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

@router.post(
    "/incidents/{incident_id}/messages",
    response_model=MessageWithAssessmentResponse,
)
def send_message(
    incident_id: str,
    body: SendMessageRequest,
    request: Request,
    engine: Engine = Depends(_engine),
) -> MessageWithAssessmentResponse:
    """Send a text message, run extraction + rules, return assistant response."""
    _verify_recaptcha(body.recaptcha_token, request, engine)

    incident_repo = IncidentRepository(engine)
    incident = incident_repo.get(incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    if incident["status"] == IncidentStatus.CLOSED.value:
        raise HTTPException(400, "Incident is closed")

    import time

    trace_id = str(uuid.uuid4())
    msg_repo = MessageRepository(engine)
    assess_repo = AssessmentRepository(engine)
    audit_repo = AuditEventRepository(engine)

    patient_msg = msg_repo.create(incident_id, "patient", body.content)

    # Step 1: Extract - try LLM first, fallback to deterministic
    t0 = time.monotonic()
    extract_model = "deterministic"
    try:
        from services.api.src.api.config import settings
        if settings.openai_api_key:
            from services.api.src.api.adapters.openai_llm import extract_medical
            extraction = extract_medical(body.content)
            extract_model = settings.openai_model_text
        else:
            extraction = extract_from_text(body.content)
    except Exception as exc:
        logger.warning("chat_extract_llm_failed", extra={"error": str(exc)})
        extraction = extract_from_text(body.content)
        extract_model = "deterministic (fallback)"
    extract_ms = int((time.monotonic() - t0) * 1000)

    # Log extraction as tool call/result
    risk_signals_summary = {}
    if hasattr(extraction, 'risk_signals') and extraction.risk_signals:
        rs = extraction.risk_signals
        risk_signals_summary = {
            "suicidal_ideation": rs.suicidal_ideation,
            "suicidal_ideation_conviction": rs.suicidal_ideation_conviction,
            "self_harm_intent": rs.self_harm_intent,
            "self_harm_intent_conviction": rs.self_harm_intent_conviction,
            "chest_pain": rs.chest_pain,
            "chest_pain_conviction": rs.chest_pain_conviction,
            "can_breathe": rs.can_breathe,
            "can_breathe_conviction": rs.can_breathe_conviction,
            "red_flags_detected": [f.value for f in rs.red_flags_detected] if rs.red_flags_detected else [],
            "missing_fields": rs.missing_fields,
        }

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="TOOL_CALL_EXTRACT",
        payload_json={
            "tool": "extract_structured",
            "schema_version": "1.0",
            "human_explanation": "Extracting structured medical information from patient message.",
        },
        model_used=extract_model,
        latency_ms=0,
    )

    # Build human explanation for risk signals
    risk_explanation_parts = []
    if extraction.risk_signals:
        rs = extraction.risk_signals
        if rs.suicidal_ideation or rs.suicidal_ideation_conviction > 0:
            risk_explanation_parts.append(f"suicidal_ideation: {rs.suicidal_ideation} (conviction: {rs.suicidal_ideation_conviction:.1f})")
        if rs.self_harm_intent or rs.self_harm_intent_conviction > 0:
            risk_explanation_parts.append(f"self_harm: {rs.self_harm_intent} (conviction: {rs.self_harm_intent_conviction:.1f})")
        if rs.chest_pain != "unknown" or rs.chest_pain_conviction > 0:
            risk_explanation_parts.append(f"chest_pain: {rs.chest_pain} (conviction: {rs.chest_pain_conviction:.1f})")
        if rs.can_breathe != "unknown" or rs.can_breathe_conviction > 0:
            risk_explanation_parts.append(f"can_breathe: {rs.can_breathe} (conviction: {rs.can_breathe_conviction:.1f})")
        if rs.neuro_deficit != "unknown" or rs.neuro_deficit_conviction > 0:
            risk_explanation_parts.append(f"neuro_deficit: {rs.neuro_deficit} (conviction: {rs.neuro_deficit_conviction:.1f})")
        if rs.bleeding_uncontrolled != "unknown" or rs.bleeding_uncontrolled_conviction > 0:
            risk_explanation_parts.append(f"bleeding: {rs.bleeding_uncontrolled} (conviction: {rs.bleeding_uncontrolled_conviction:.1f})")

    risk_explanation = "; ".join(risk_explanation_parts) if risk_explanation_parts else "No critical risk signals detected."

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="TOOL_RESULT_EXTRACT",
        payload_json={
            "tool": "extract_structured",
            "symptoms_count": len(extraction.symptoms),
            "pain_scale": extraction.pain_scale,
            "mental_status": extraction.mental_status,
            "risk_signals": risk_signals_summary,
            "human_explanation": f"Extracted {len(extraction.symptoms)} symptoms, pain scale {extraction.pain_scale or 'not provided'}, mental status: {extraction.mental_status}. Risk signals: {risk_explanation}",
        },
        model_used=extract_model,
        latency_ms=extract_ms,
    )

    # Step 2: Triage Rules (always deterministic)
    t0 = time.monotonic()
    assessment_result = assess(extraction)
    rules_ms = int((time.monotonic() - t0) * 1000)

    # Build human-readable explanation of rules result
    triggered_flags_list = []
    if hasattr(assessment_result, 'triggered_risk_flags') and assessment_result.triggered_risk_flags:
        triggered_flags_list = [trf.flag_type.value for trf in assessment_result.triggered_risk_flags]

    rules_human_explanation = f"ESI-{assessment_result.acuity} triage level."
    if assessment_result.escalate:
        rules_human_explanation += " ESCALATION REQUIRED."
    if triggered_flags_list:
        rules_human_explanation += f" Triggered flags: {', '.join(triggered_flags_list)}."
    if assessment_result.red_flags:
        rules_human_explanation += f" {len(assessment_result.red_flags)} red flags detected."

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="TOOL_CALL_RULES",
        payload_json={
            "tool": "evaluate_rules",
            "rule_set_version": "1.0",
            "thresholds_version": "1.0",
            "human_explanation": "Evaluating deterministic triage rules against extracted data.",
        },
        model_used="rules.py (deterministic)",
        latency_ms=0,
    )

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="TOOL_RESULT_RULES",
        payload_json={
            "tool": "evaluate_rules",
            "acuity": assessment_result.acuity,
            "escalate": assessment_result.escalate,
            "disposition": assessment_result.disposition,
            "triggered_risk_flags": triggered_flags_list,
            "red_flags_count": len(assessment_result.red_flags),
            "human_explanation": rules_human_explanation,
        },
        model_used="rules.py (deterministic)",
        latency_ms=rules_ms,
    )

    assessment_row = assess_repo.create(
        incident_id=incident_id,
        domain=incident["domain"],
        result_json=assessment_result.model_dump(),
    )

    # Update severity based on acuity
    severity = ACUITY_TO_SEVERITY.get(assessment_result.acuity, Severity.UNASSIGNED)
    incident_repo.update_severity(incident_id, severity.value)

    # Append user message to history
    incident_repo.append_interaction(incident_id, {
        "type": "user_message",
        "ts": _str_dt(patient_msg["created_at"]),
        "message_id": patient_msg["id"],
        "content": body.content,
        "source": "chat",
    })

    # Append assessment to history
    incident_repo.append_interaction(incident_id, {
        "type": "assessment",
        "ts": _str_dt(assessment_row["created_at"]),
        "assessment_id": assessment_row["id"],
        "acuity": assessment_result.acuity,
        "severity": severity.value,
        "disposition": assessment_result.disposition,
        "escalate": assessment_result.escalate,
        "red_flags": [{"name": rf.name, "reason": rf.reason} for rf in assessment_result.red_flags],
    })

    if assessment_result.escalate:
        incident_repo.update_status(incident_id, IncidentStatus.ESCALATED.value)

    # Step 3: Generate Response
    t0 = time.monotonic()
    assistant_text = _generate_response(extraction, assessment_result)
    response_ms = int((time.monotonic() - t0) * 1000)
    assistant_msg = msg_repo.create(incident_id, "assistant", assistant_text)

    # Append assistant response to history
    incident_repo.append_interaction(incident_id, {
        "type": "assistant_message",
        "ts": _str_dt(assistant_msg["created_at"]),
        "message_id": assistant_msg["id"],
        "content": assistant_text,
        "source": "chat",
        "model": "deterministic (rule-based)",
    })

    # Determine action taken
    if assessment_result.escalate:
        action = "escalate"
        action_reason = "Critical risk signals or red flags detected requiring immediate medical attention."
    elif assessment_result.disposition == "discharge":
        action = "advise"
        action_reason = "Minor symptoms with no concerning findings. Providing self-care guidance."
    else:
        action = "ask"
        action_reason = "Need more information to complete triage assessment."

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="AGENT_DECISION",
        payload_json={
            "action": action,
            "disposition": assessment_result.disposition,
            "human_explanation": action_reason,
        },
        model_used="deterministic (rule-based)",
        latency_ms=response_ms,
    )

    logger.info("message_processed", extra={
        "incident_id": incident_id,
        "trace_id": trace_id,
        "acuity": assessment_result.acuity,
        "severity": severity.value,
    })

    return MessageWithAssessmentResponse(
        message=MessageResponse(
            id=patient_msg["id"],
            incident_id=incident_id,
            role=patient_msg["role"],
            content_text=patient_msg["content_text"],
            created_at=_str_dt(patient_msg["created_at"]),
        ),
        assistant_message=MessageResponse(
            id=assistant_msg["id"],
            incident_id=incident_id,
            role=assistant_msg["role"],
            content_text=assistant_msg["content_text"],
            created_at=_str_dt(assistant_msg["created_at"]),
        ),
        assessment=AssessmentResponse(
            id=assessment_row["id"],
            incident_id=incident_id,
            domain=assessment_row["domain"],
            result_json=assessment_result.model_dump(),
            created_at=_str_dt(assessment_row["created_at"]),
        ),
    )


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

@router.get("/incidents/{incident_id}/timeline", response_model=TimelineResponse)
def get_timeline(
    incident_id: str,
    engine: Engine = Depends(_engine),
) -> TimelineResponse:
    """Get the audit event timeline for an incident."""
    incident_repo = IncidentRepository(engine)
    if not incident_repo.get(incident_id):
        raise HTTPException(404, "Incident not found")

    audit_repo = AuditEventRepository(engine)
    events = audit_repo.list_by_incident(incident_id)

    return TimelineResponse(
        incident_id=incident_id,
        events=[
            AuditEventResponse(
                id=e["id"],
                incident_id=e["incident_id"],
                trace_id=e["trace_id"],
                step=e["step"],
                payload_json=e["payload_json"],
                latency_ms=e["latency_ms"],
                model_used=e["model_used"],
                token_usage_json=e["token_usage_json"],
                created_at=_str_dt(e["created_at"]),
            )
            for e in events
        ],
    )


# ---------------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------------

@router.post("/incidents/{incident_id}/voice", response_model=VoiceResponse)
async def send_voice(
    incident_id: str,
    request: Request,
    audio: UploadFile,
    recaptcha_token: str = Form(""),
    engine: Engine = Depends(_engine),
) -> VoiceResponse:
    """Voice pipeline: STT → Extract → Rules → Generate → TTS."""
    _verify_recaptcha(recaptcha_token or None, request, engine)

    incident_repo = IncidentRepository(engine)
    incident = incident_repo.get(incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found")
    if incident["status"] == IncidentStatus.CLOSED.value:
        raise HTTPException(400, "Incident is closed")

    audio_bytes = await audio.read()
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "Audio file too large (max 10 MB)")

    from starlette.concurrency import run_in_threadpool
    from services.api.src.api.core.pipeline import run_voice_pipeline

    result = await run_in_threadpool(
        run_voice_pipeline,
        incident_id=incident_id,
        audio_bytes=audio_bytes,
        filename=audio.filename or "audio.webm",
        engine=engine,
    )

    assessment_resp = None
    if result.assessment_row:
        assessment_resp = AssessmentResponse(
            id=result.assessment_row["id"],
            incident_id=incident_id,
            domain=result.assessment_row["domain"],
            result_json=result.assessment_row["result_json"]
            if isinstance(result.assessment_row["result_json"], dict)
            else {},
            created_at=_str_dt(result.assessment_row["created_at"]),
        )

    return VoiceResponse(
        transcript=result.transcript,
        response_text=result.response_text,
        audio_base64=result.audio_base64,
        assessment=assessment_resp,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_response(
    extraction: MedicalExtraction,
    assessment,
) -> str:
    """Generate a deterministic assistant response for text chat.

    SAFETY: If any red flags or triggered risk flags exist, we NEVER
    return a "minor concern" message. Escalation takes priority.
    """
    # Check for escalation - either explicit or via risk flags
    has_risk_flags = getattr(assessment, 'triggered_risk_flags', None) and len(assessment.triggered_risk_flags) > 0
    has_red_flags = assessment.red_flags and len(assessment.red_flags) > 0

    if assessment.escalate or has_risk_flags:
        # Build escalation message with reason if available
        base_msg = (
            "Based on what you've told me, this requires immediate medical attention. "
            "I'm escalating your case to a medical professional right away."
        )
        # Add specific reason if we have triggered risk flags
        if has_risk_flags and hasattr(assessment, 'escalation_reason') and assessment.escalation_reason:
            return f"{base_msg}\n\nReason: {assessment.escalation_reason}"
        return base_msg

    # SAFETY: Never say "minor concern" if there are any red flags
    if has_red_flags:
        return (
            "I've noted some concerns in what you've described. "
            "Please continue to describe your symptoms so I can complete your assessment."
        )

    if assessment.disposition == "discharge":
        return (
            "Based on your symptoms, this appears to be a minor concern. "
            "Please monitor your symptoms and seek care if they worsen."
        )

    if not extraction.symptoms:
        return "Can you describe your symptoms in more detail?"
    if extraction.pain_scale is None:
        return "On a scale of 0-10, how would you rate your pain?"
    if not extraction.medical_history:
        return "Do you have any relevant medical history I should know about?"
    if not extraction.allergies:
        return "Do you have any known allergies?"
    if not extraction.medications:
        return "Are you currently taking any medications?"

    return "Thank you. I have enough information to complete your triage assessment."
