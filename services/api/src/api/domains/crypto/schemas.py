"""Pydantic schemas for crypto/DeFi incident extraction and assessment."""

from __future__ import annotations

from pydantic import Field

from services.api.src.api.domains.schemas import BaseAssessment, BaseExtraction, BaseRedFlag


class CryptoExtraction(BaseExtraction):
    """Structured extraction from crypto/DeFi incident report."""

    protocol: str = Field("", description="DeFi protocol name")
    chain: str = Field("", description="Blockchain (ethereum, polygon, etc)")
    symbol: str = Field("", description="Token symbol if applicable")
    incident_type: str = Field(
        "", description="Type: price_crash|exploit|liquidity|oracle|governance"
    )
    description: str = Field("", description="What happened")
    affected_pools: list[str] = Field(default_factory=list)
    tvl_at_risk: float = Field(0.0, ge=0, description="Total value locked at risk in USD")
    price_change_pct: float | None = Field(None, description="Price change percentage")
    timeframe: str = Field("", description="Timeframe of the incident")
    tx_hashes: list[str] = Field(default_factory=list, description="Relevant transaction hashes")
    source_url: str = Field("", description="Source of the report")


class CryptoRedFlag(BaseRedFlag):
    """A detected crypto red-flag condition."""

    tvl_impact: float = Field(0.0, description="TVL impact in USD")


class CryptoAssessment(BaseAssessment):
    """Crypto incident assessment result."""

    risk_level: str = Field("medium", description="low|medium|high|critical")
    red_flags: list[CryptoRedFlag] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    requires_position_review: bool = Field(False, description="Whether to review positions")
    affected_positions: list[str] = Field(default_factory=list)
