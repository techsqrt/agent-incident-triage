"""Base interface for domain modules.

All domain-specific logic must implement this interface.
The core pipeline depends only on DomainModule, not on hardcoded domain checks.
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class DomainModule(ABC):
    """Abstract base class for domain modules.

    Each domain (medical, sre, crypto) must implement this interface.
    This ensures consistent behavior across domains and makes adding
    new domains a matter of implementing this interface + registering.
    """

    @property
    @abstractmethod
    def domain_key(self) -> str:
        """Unique identifier for this domain (e.g., 'medical', 'sre')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for UI display."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of what this domain handles."""
        ...

    @abstractmethod
    def get_extraction_schema(self) -> type[BaseModel]:
        """Return the Pydantic schema for LLM extraction."""
        ...

    @abstractmethod
    def get_assessment_schema(self) -> type[BaseModel]:
        """Return the Pydantic schema for assessment results."""
        ...

    @abstractmethod
    def assess(self, extraction: BaseModel) -> BaseModel:
        """Run deterministic rules on extraction, return assessment.

        Args:
            extraction: Domain-specific extraction (must match get_extraction_schema)

        Returns:
            Assessment result (must match get_assessment_schema)
        """
        ...

    @abstractmethod
    def get_severity_label(self, assessment: BaseModel) -> str:
        """Map assessment to a human-readable severity label.

        Returns one of: 'critical', 'high', 'medium', 'low'
        Used for filtering and display in the UI.
        """
        ...

    @abstractmethod
    def explain_event(self, event_type: str, event_data: dict[str, Any]) -> str:
        """Convert an audit event to human-readable explanation.

        Args:
            event_type: The step/type of event (e.g., 'STT', 'EXTRACT', 'TRIAGE')
            event_data: The event payload (redacted)

        Returns:
            Human-friendly explanation of what happened and why
        """
        ...

    def get_extraction_prompt(self) -> str:
        """Return the prompt template for LLM extraction.

        Override in subclass if domain has custom prompts.
        """
        return ""

    def get_response_prompt(self) -> str:
        """Return the prompt template for LLM response generation.

        Override in subclass if domain has custom prompts.
        """
        return ""
