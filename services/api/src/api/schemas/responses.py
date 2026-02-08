"""Pydantic request/response models for triage API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


# -- Requests ---------------------------------------------------------------

class CreateIncidentRequest(BaseModel):
    domain: str
    mode: str = "B"


class SendMessageRequest(BaseModel):
    content: str
    recaptcha_token: str | None = None


# -- Responses ---------------------------------------------------------------

class IncidentResponse(BaseModel):
    id: str
    domain: str
    status: str
    mode: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    incident_id: str
    role: str
    content_text: str
    created_at: str


class AssessmentResponse(BaseModel):
    id: str
    incident_id: str
    domain: str
    result_json: dict
    created_at: str


class AuditEventResponse(BaseModel):
    id: str
    incident_id: str
    trace_id: str
    step: str
    payload_json: dict
    latency_ms: int | None
    model_used: str | None
    token_usage_json: dict | None
    created_at: str


class TimelineResponse(BaseModel):
    incident_id: str
    events: list[AuditEventResponse]


class MessageWithAssessmentResponse(BaseModel):
    message: MessageResponse
    assistant_message: MessageResponse
    assessment: AssessmentResponse | None = None


class VoiceResponse(BaseModel):
    transcript: str
    response_text: str
    audio_base64: str | None = None
    assessment: AssessmentResponse | None = None
