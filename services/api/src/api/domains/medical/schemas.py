"""Pydantic schemas for medical triage extraction and assessment."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from services.api.src.api.domains.schemas import BaseAssessment, BaseExtraction, BaseRedFlag


class CriticalRedFlagType(str, Enum):
    """Enumeration of critical red flags requiring immediate escalation."""

    SUICIDAL_IDEATION = "SUICIDAL_IDEATION"
    SELF_HARM = "SELF_HARM"
    HOMICIDAL_IDEATION = "HOMICIDAL_IDEATION"
    CANNOT_BREATHE = "CANNOT_BREATHE"
    CHEST_PAIN = "CHEST_PAIN"
    NEURO_DEFICIT = "NEURO_DEFICIT"
    BLEEDING_UNCONTROLLED = "BLEEDING_UNCONTROLLED"
    ALTERED_CONSCIOUSNESS = "ALTERED_CONSCIOUSNESS"
    SEVERE_PAIN = "SEVERE_PAIN"


# Type alias for risk signal values
RiskSignalValue = Literal["yes", "no", "unknown"]


class RiskSignals(BaseModel):
    """Critical risk signals extracted from patient conversation.

    These signals are used for deterministic escalation decisions.
    Each signal has a boolean/tri-state value AND a conviction score (0.0-1.0).

    Conviction rules:
    - If a boolean is true, conviction should be >= 0.8
    - If a boolean is false, conviction should be <= 0.2
    - If unknown, conviction should be 0.0
    """

    # Critical psychiatric signals (boolean)
    suicidal_ideation: bool = Field(False, description="Patient expresses suicidal thoughts")
    suicidal_ideation_conviction: float = Field(0.0, ge=0.0, le=1.0)

    self_harm_intent: bool = Field(False, description="Patient expresses intent to self-harm")
    self_harm_intent_conviction: float = Field(0.0, ge=0.0, le=1.0)

    homicidal_ideation: bool = Field(False, description="Patient expresses intent to harm others")
    homicidal_ideation_conviction: float = Field(0.0, ge=0.0, le=1.0)

    # Critical physical signals (tri-state: yes/no/unknown)
    can_breathe: RiskSignalValue = Field("unknown", description="Patient can breathe normally")
    can_breathe_conviction: float = Field(0.0, ge=0.0, le=1.0)

    chest_pain: RiskSignalValue = Field("unknown", description="Patient has chest pain")
    chest_pain_conviction: float = Field(0.0, ge=0.0, le=1.0)

    neuro_deficit: RiskSignalValue = Field("unknown", description="Neurological deficit present")
    neuro_deficit_conviction: float = Field(0.0, ge=0.0, le=1.0)

    bleeding_uncontrolled: RiskSignalValue = Field("unknown", description="Uncontrolled bleeding")
    bleeding_uncontrolled_conviction: float = Field(0.0, ge=0.0, le=1.0)

    # Pain assessment
    pain_scale_0_10: int | None = Field(None, ge=0, le=10, description="Pain scale 0-10")

    # Detected critical red flags (computed from above signals)
    red_flags_detected: list[CriticalRedFlagType] = Field(
        default_factory=list, description="Critical red flags triggered"
    )

    # Missing fields that would help triage
    missing_fields: list[str] = Field(
        default_factory=list, description="Key fields missing for complete triage"
    )


class VitalSigns(BaseExtraction):
    """Patient vital signs extracted from conversation."""

    heart_rate: int | None = Field(None, ge=0, le=300, description="BPM")
    blood_pressure_systolic: int | None = Field(None, ge=0, le=300)
    blood_pressure_diastolic: int | None = Field(None, ge=0, le=200)
    respiratory_rate: int | None = Field(None, ge=0, le=60)
    temperature_f: float | None = Field(None, ge=80.0, le=115.0)
    oxygen_saturation: int | None = Field(None, ge=0, le=100)


class MedicalExtraction(BaseExtraction):
    """Structured extraction from patient conversation via LLM."""

    chief_complaint: str = Field("", description="Primary reason for visit")
    symptoms: list[str] = Field(default_factory=list)
    pain_scale: int | None = Field(None, ge=0, le=10)
    vitals: VitalSigns = Field(default_factory=VitalSigns)
    medical_history: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    onset: str = Field("", description="When symptoms started")
    mental_status: str = Field("alert", description="alert|confused|unresponsive")

    # Risk signals for deterministic escalation
    risk_signals: RiskSignals = Field(default_factory=RiskSignals)


class RedFlag(BaseRedFlag):
    """A detected medical red-flag condition."""

    pass


class TriggeredRiskFlag(BaseModel):
    """A risk flag that was triggered by threshold evaluation."""

    flag_type: CriticalRedFlagType
    signal_value: str = Field(..., description="The signal value that triggered this")
    conviction: float = Field(..., ge=0.0, le=1.0)
    threshold: float = Field(..., ge=0.0, le=1.0)
    human_explanation: str = Field(..., description="User-friendly explanation")


class MedicalAssessment(BaseAssessment):
    """Deterministic triage assessment result."""

    acuity: int = Field(..., ge=1, le=5, description="ESI level 1-5")
    red_flags: list[RedFlag] = Field(default_factory=list)

    # Risk signal evaluation results
    triggered_risk_flags: list[TriggeredRiskFlag] = Field(
        default_factory=list, description="Risk flags that triggered escalation"
    )
    escalation_reason: str = Field("", description="Human-readable escalation reason")
