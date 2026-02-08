"""Pydantic schemas for medical triage extraction and assessment."""

from __future__ import annotations

from pydantic import Field

from services.api.src.api.domains.schemas import BaseAssessment, BaseExtraction, BaseRedFlag


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


class RedFlag(BaseRedFlag):
    """A detected medical red-flag condition."""

    pass


class MedicalAssessment(BaseAssessment):
    """Deterministic triage assessment result."""

    acuity: int = Field(..., ge=1, le=5, description="ESI level 1-5")
    red_flags: list[RedFlag] = Field(default_factory=list)
