"""Base schemas for all domain extractions and assessments.

All domain-specific schemas should inherit from these base classes
to ensure consistent structure across domains.
"""

from abc import ABC
from datetime import datetime

from pydantic import BaseModel, Field


class BaseExtraction(BaseModel, ABC):
    """Abstract base for all domain extractions.

    Common fields that every extraction should have, regardless of domain.
    Domain-specific extractions add their own fields on top of these.
    """

    raw_input: str = Field("", description="Original user input text")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="LLM extraction confidence")
    extracted_at: datetime | None = Field(None, description="When extraction occurred")


class BaseRedFlag(BaseModel):
    """A detected red-flag condition common across domains."""

    name: str = Field(..., description="Short identifier for the red flag")
    reason: str = Field(..., description="Why this was flagged")
    severity: str = Field("high", description="low|medium|high|critical")


class BaseAssessment(BaseModel, ABC):
    """Abstract base for all domain assessments.

    Common fields that every assessment should have.
    Domain-specific assessments add their own fields.
    """

    escalate: bool = Field(False, description="Whether to escalate to human")
    severity_score: int = Field(
        5, ge=1, le=10, description="Normalized severity 1-10 (10=most severe)"
    )
    disposition: str = Field("continue", description="continue|escalate|resolve")
    summary: str = Field("", description="Human-readable assessment summary")
    assessed_at: datetime | None = Field(None, description="When assessment occurred")
