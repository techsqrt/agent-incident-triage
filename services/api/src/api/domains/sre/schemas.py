"""Pydantic schemas for SRE incident extraction and assessment."""

from __future__ import annotations

from pydantic import Field

from services.api.src.api.domains.schemas import BaseAssessment, BaseExtraction, BaseRedFlag


class SREExtraction(BaseExtraction):
    """Structured extraction from SRE incident report."""

    service: str = Field("", description="Affected service name")
    region: str = Field("", description="Affected region/datacenter")
    error_type: str = Field("", description="Type of error (timeout, 5xx, memory, etc)")
    error_message: str = Field("", description="Error message or stack trace snippet")
    impact: str = Field("", description="User/business impact description")
    start_time: str = Field("", description="When the incident started")
    affected_endpoints: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(
        default_factory=dict, description="Key metrics (error_rate, latency_p99, etc)"
    )
    alert_source: str = Field("", description="Where the alert came from (PagerDuty, etc)")
    runbook_url: str = Field("", description="Link to relevant runbook")


class SRERedFlag(BaseRedFlag):
    """A detected SRE red-flag condition."""

    affected_users: int = Field(0, description="Estimated affected users")


class SREAssessment(BaseAssessment):
    """SRE incident assessment result."""

    priority: str = Field("P3", description="P1|P2|P3|P4")
    red_flags: list[SRERedFlag] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    estimated_impact_users: int = Field(0, ge=0)
    requires_page: bool = Field(False, description="Whether to page on-call")
