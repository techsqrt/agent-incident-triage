"""Crypto domain module implementation (placeholder)."""

from typing import Any

from pydantic import BaseModel

from services.api.src.api.domains.base import DomainModule
from services.api.src.api.domains.crypto.schemas import CryptoAssessment, CryptoExtraction


class CryptoDomainModule(DomainModule):
    """Crypto/DeFi incident triage domain module."""

    @property
    def domain_key(self) -> str:
        return "crypto"

    @property
    def display_name(self) -> str:
        return "Crypto/DeFi"

    @property
    def description(self) -> str:
        return "DeFi protocol and crypto market incident triage"

    def get_extraction_schema(self) -> type[BaseModel]:
        return CryptoExtraction

    def get_assessment_schema(self) -> type[BaseModel]:
        return CryptoAssessment

    def assess(self, extraction: BaseModel) -> BaseModel:
        """Placeholder assessment - returns default values."""
        if not isinstance(extraction, CryptoExtraction):
            raise TypeError(f"Expected CryptoExtraction, got {type(extraction)}")
        return CryptoAssessment(
            risk_level="medium",
            escalate=False,
            severity_score=5,
            disposition="continue",
            summary="Assessment pending implementation",
        )

    def get_severity_label(self, assessment: BaseModel) -> str:
        if not isinstance(assessment, CryptoAssessment):
            raise TypeError(f"Expected CryptoAssessment, got {type(assessment)}")
        return assessment.risk_level

    def explain_event(self, event_type: str, event_data: dict[str, Any]) -> str:
        return f"Processing step: {event_type}"

    def get_extraction_prompt(self) -> str:
        return "Extract crypto/DeFi incident details from the conversation."

    def get_response_prompt(self) -> str:
        return "You are a DeFi analyst helping triage protocol incidents."


crypto_module = CryptoDomainModule()
