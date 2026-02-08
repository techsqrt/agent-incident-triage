"""Pydantic schemas for database records and history interactions."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ============================================================================
# History Interaction Types
# ============================================================================

InteractionType = Literal[
    # User actions
    "user_sent",           # User sent a message (chat or voice)
    "user_closed",         # User closed the incident
    "user_reopened",       # User reopened the incident
    "user_feedback",       # User provided feedback/rating

    # Agent processing
    "agent_received",      # Agent received and acknowledged input
    "agent_transcribed",   # Voice transcribed to text (STT)
    "agent_extracted",     # LLM extracted structured data
    "agent_reasoned",      # Rules engine ran, classification done
    "agent_responded",     # Agent generated response
    "agent_synthesized",   # Text converted to speech (TTS)
    "agent_escalated",     # Agent triggered escalation

    # System events
    "system_created",      # Incident created
    "system_timeout",      # Session timed out
    "system_error",        # Error occurred
    "system_migrated",     # Data migrated/updated
]


class BaseInteraction(BaseModel):
    """Base class for all history interactions."""
    type: InteractionType
    ts: datetime = Field(default_factory=datetime.utcnow)


class UserSentInteraction(BaseInteraction):
    """User sent a message."""
    type: Literal["user_sent"] = "user_sent"
    content: str
    mode: Literal["chat", "voice"] = "chat"
    audio_duration_ms: int | None = None


class UserClosedInteraction(BaseInteraction):
    """User closed the incident."""
    type: Literal["user_closed"] = "user_closed"
    reason: str = ""


class UserReopenedInteraction(BaseInteraction):
    """User reopened the incident."""
    type: Literal["user_reopened"] = "user_reopened"
    reason: str = ""


class UserFeedbackInteraction(BaseInteraction):
    """User provided feedback."""
    type: Literal["user_feedback"] = "user_feedback"
    rating: int | None = Field(None, ge=1, le=5)
    comment: str = ""


class AgentTranscribedInteraction(BaseInteraction):
    """Voice transcribed to text."""
    type: Literal["agent_transcribed"] = "agent_transcribed"
    model: str
    transcript: str
    confidence: float | None = None
    latency_ms: int


class AgentExtractedInteraction(BaseInteraction):
    """LLM extracted structured data."""
    type: Literal["agent_extracted"] = "agent_extracted"
    model: str
    extraction: dict[str, Any]
    confidence: float | None = None
    latency_ms: int
    tokens_input: int | None = None
    tokens_output: int | None = None


class AgentReasonedInteraction(BaseInteraction):
    """Rules engine processed extraction."""
    type: Literal["agent_reasoned"] = "agent_reasoned"
    rules_applied: list[str] = Field(default_factory=list)
    classification: dict[str, Any] = Field(default_factory=dict)
    red_flags: list[dict[str, Any]] = Field(default_factory=list)
    escalate: bool = False
    acuity: int | None = None
    severity_score: int | None = None


class AgentRespondedInteraction(BaseInteraction):
    """Agent generated response."""
    type: Literal["agent_responded"] = "agent_responded"
    model: str
    content: str
    latency_ms: int
    tokens_input: int | None = None
    tokens_output: int | None = None


class AgentSynthesizedInteraction(BaseInteraction):
    """Text converted to speech."""
    type: Literal["agent_synthesized"] = "agent_synthesized"
    model: str
    audio_duration_ms: int
    latency_ms: int


class AgentEscalatedInteraction(BaseInteraction):
    """Agent triggered escalation."""
    type: Literal["agent_escalated"] = "agent_escalated"
    reason: str
    red_flags: list[str] = Field(default_factory=list)
    acuity: int | None = None
    severity_score: int | None = None


class SystemCreatedInteraction(BaseInteraction):
    """Incident created."""
    type: Literal["system_created"] = "system_created"
    domain: str
    mode: Literal["chat", "voice"]
    client_ip: str | None = None
    client_ua: str | None = None


class SystemErrorInteraction(BaseInteraction):
    """Error occurred."""
    type: Literal["system_error"] = "system_error"
    error_type: str
    error_message: str
    step: str | None = None


# ============================================================================
# Diagnostic Schema
# ============================================================================

class IncidentDiagnostic(BaseModel):
    """Diagnostic metadata for an incident."""
    # Model info
    model_extraction: str | None = None
    model_response: str | None = None
    model_stt: str | None = None
    model_tts: str | None = None

    # Aggregate stats
    total_latency_ms: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    interaction_count: int = 0

    # Client info (redacted as needed)
    client_ip_hash: str | None = None
    client_ua: str | None = None

    # Feature flags active during incident
    feature_flags: list[str] = Field(default_factory=list)

    # Version info
    api_version: str | None = None
    domain_rules_version: str | None = None


# ============================================================================
# History Container
# ============================================================================

class IncidentHistory(BaseModel):
    """Container for all incident interactions."""
    interactions: list[dict[str, Any]] = Field(default_factory=list)

    def append(self, interaction: BaseInteraction) -> None:
        """Add an interaction to history."""
        self.interactions.append(interaction.model_dump(mode="json"))

    def get_by_type(self, interaction_type: InteractionType) -> list[dict[str, Any]]:
        """Get all interactions of a specific type."""
        return [i for i in self.interactions if i.get("type") == interaction_type]


# ============================================================================
# Incident Record
# ============================================================================

class IncidentRecord(BaseModel):
    """Full incident record for API responses."""
    id: str
    domain: str
    status: str
    mode: str
    created_at: datetime
    updated_at: datetime
    ts_escalated: datetime | None = None
    diagnostic: IncidentDiagnostic = Field(default_factory=IncidentDiagnostic)
    history: IncidentHistory = Field(default_factory=IncidentHistory)
