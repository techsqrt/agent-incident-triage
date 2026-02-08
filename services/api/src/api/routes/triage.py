"""Triage API endpoints."""

import logging
import os
import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
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

MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
from services.api.src.api.schemas.responses import (
    AssessmentResponse,
    AuditEventResponse,
    CreateIncidentRequest,
    IncidentResponse,
    MessageResponse,
    MessageWithAssessmentResponse,
    SendMessageRequest,
    TimelineResponse,
    VoiceResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_client_ip(request: Request) -> str:
    """Get client IP from request, handling proxies."""
    # Check X-Forwarded-For header (set by proxies/load balancers)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Take the first IP (original client)
        return forwarded.split(",")[0].strip()
    # Fall back to direct connection IP
    return request.client.host if request.client else "unknown"


def _verify_recaptcha(token: str | None, request: Request, engine: Engine) -> None:
    """Verify reCAPTCHA token if secret key is configured. Caches verified IPs for 7 days."""
    recaptcha_secret = settings.recaptcha_secret_key
    if not recaptcha_secret:
        return  # reCAPTCHA not configured, skip verification

    client_ip = _get_client_ip(request)
    ip_repo = VerifiedIPRepository(engine)

    # Check if IP is already verified
    if ip_repo.is_verified(client_ip):
        logger.info("recaptcha_ip_cached", extra={"ip": client_ip})
        return

    if not token:
        raise HTTPException(403, "reCAPTCHA token required")

    import httpx
    resp = httpx.post(
        "https://www.google.com/recaptcha/api/siteverify",
        data={
            "secret": recaptcha_secret,
            "response": token,
        },
    )
    result = resp.json()
    logger.info("recaptcha_google_response", extra={"ip": client_ip, "result": result})

    if not result.get("success"):
        error_codes = result.get("error-codes", [])
        logger.warning("recaptcha_verification_failed", extra={"ip": client_ip, "errors": error_codes})
        raise HTTPException(403, f"reCAPTCHA verification failed: {error_codes}")

    # Store verified IP for 7 days
    ip_repo.add(client_ip)
    logger.info("recaptcha_ip_verified", extra={"ip": client_ip})


def _engine() -> Engine:
    return get_engine()


def _str_dt(dt) -> str:
    """Convert a datetime to ISO string."""
    return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)


# ---------------------------------------------------------------------------
# Debug endpoint (temporary - for diagnosing production issues)
# ---------------------------------------------------------------------------

@router.get("/debug/db")
def debug_db(engine: Engine = Depends(_engine)) -> dict:
    """Debug endpoint to check database status."""
    from sqlalchemy import text, inspect
    result = {"tables": [], "errors": []}
    try:
        inspector = inspect(engine)
        result["tables"] = inspector.get_table_names()
        result["db_url_masked"] = str(engine.url).split("@")[-1] if "@" in str(engine.url) else "local"
    except Exception as e:
        result["errors"].append(f"inspect: {e}")

    # Test verified_ips
    try:
        with engine.connect() as conn:
            r = conn.execute(text("SELECT COUNT(*) FROM verified_ips"))
            result["verified_ips_count"] = r.scalar()
    except Exception as e:
        result["errors"].append(f"verified_ips: {e}")

    # Test triage_incidents
    try:
        with engine.connect() as conn:
            r = conn.execute(text("SELECT COUNT(*) FROM triage_incidents"))
            result["incidents_count"] = r.scalar()
    except Exception as e:
        result["errors"].append(f"triage_incidents: {e}")

    return result


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
        # reCAPTCHA not configured, no verification needed
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
    if body.domain not in ALL_DOMAINS:
        raise HTTPException(400, f"Unknown domain: {body.domain}")
    if not is_domain_active(body.domain):
        raise HTTPException(400, f"Domain '{body.domain}' is not active")
    if body.mode not in ("A", "B"):
        raise HTTPException(400, f"Invalid mode: {body.mode}")

    repo = IncidentRepository(engine)
    row = repo.create(domain=body.domain, mode=body.mode)

    logger.info("incident_created", extra={
        "incident_id": row["id"], "domain": body.domain,
    })

    return IncidentResponse(
        id=row["id"],
        domain=row["domain"],
        status=row["status"],
        mode=row["mode"],
        created_at=_str_dt(row["created_at"]),
        updated_at=_str_dt(row["updated_at"]),
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
        created_at=_str_dt(row["created_at"]),
        updated_at=_str_dt(row["updated_at"]),
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
    if incident["status"] == "CLOSED":
        raise HTTPException(400, "Incident is closed")

    trace_id = str(uuid.uuid4())
    msg_repo = MessageRepository(engine)
    assess_repo = AssessmentRepository(engine)
    audit_repo = AuditEventRepository(engine)

    # 1) Persist patient message
    patient_msg = msg_repo.create(incident_id, "patient", body.content)

    # 2) Run deterministic keyword extraction (text chat stays deterministic)
    extraction = extract_from_text(body.content)

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="EXTRACT",
        payload_json=redact_dict(extraction.model_dump()),
        model_used="deterministic",
    )

    # 3) Run deterministic triage rules
    assessment_result = assess(extraction)

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="TRIAGE_RULES",
        payload_json={"acuity": assessment_result.acuity, "escalate": assessment_result.escalate},
    )

    # 4) Persist assessment
    assessment_row = assess_repo.create(
        incident_id=incident_id,
        domain=incident["domain"],
        result_json=assessment_result.model_dump(),
    )

    # 5) Update incident status if escalation needed
    if assessment_result.escalate:
        incident_repo.update_status(incident_id, "ESCALATED")

    # 6) Generate assistant response (simple for now — LLM adapter in M5)
    assistant_text = _generate_response(extraction, assessment_result)
    assistant_msg = msg_repo.create(incident_id, "assistant", assistant_text)

    audit_repo.append(
        incident_id=incident_id,
        trace_id=trace_id,
        step="RESPONSE_GENERATED",
        payload_json={"disposition": assessment_result.disposition},
    )

    logger.info("message_processed", extra={
        "incident_id": incident_id,
        "trace_id": trace_id,
        "acuity": assessment_result.acuity,
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
    if incident["status"] == "CLOSED":
        raise HTTPException(400, "Incident is closed")

    # Reads full upload then checks size — returns a clear 413 JSON error
    # so the client can show a friendly message instead of a raw failure.
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
    """Generate a deterministic assistant response for text chat."""
    if assessment.escalate:
        return (
            "Based on what you've told me, this requires immediate medical attention. "
            "I'm escalating your case to a medical professional right away."
        )

    if assessment.disposition == "discharge":
        return (
            "Based on your symptoms, this appears to be a minor concern. "
            "Please monitor your symptoms and seek care if they worsen."
        )

    # Ask follow-up
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
