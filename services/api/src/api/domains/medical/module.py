"""Medical domain module implementation."""

from typing import Any

from pydantic import BaseModel

from services.api.src.api.domains.base import DomainModule
from services.api.src.api.domains.medical.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    FOLLOWUP_SYSTEM_PROMPT,
)
from services.api.src.api.domains.medical.rules import assess as medical_assess
from services.api.src.api.domains.medical.schemas import (
    MedicalAssessment,
    MedicalExtraction,
)


class MedicalDomainModule(DomainModule):
    """Medical triage domain module.

    Handles patient intake, symptom extraction, and ESI-like triage
    with deterministic rules for escalation decisions.
    """

    @property
    def domain_key(self) -> str:
        return "medical"

    @property
    def display_name(self) -> str:
        return "Medical Triage"

    @property
    def description(self) -> str:
        return "Voice-powered medical triage with symptom extraction and urgency assessment"

    def get_extraction_schema(self) -> type[BaseModel]:
        return MedicalExtraction

    def get_assessment_schema(self) -> type[BaseModel]:
        return MedicalAssessment

    def assess(self, extraction: BaseModel) -> BaseModel:
        if not isinstance(extraction, MedicalExtraction):
            raise TypeError(f"Expected MedicalExtraction, got {type(extraction)}")
        return medical_assess(extraction)

    def get_severity_label(self, assessment: BaseModel) -> str:
        if not isinstance(assessment, MedicalAssessment):
            raise TypeError(f"Expected MedicalAssessment, got {type(assessment)}")

        # Map ESI acuity to severity labels
        # ESI 1-2 = critical/high (escalate)
        # ESI 3 = medium
        # ESI 4-5 = low
        if assessment.acuity <= 1:
            return "critical"
        elif assessment.acuity == 2:
            return "high"
        elif assessment.acuity == 3:
            return "medium"
        else:
            return "low"

    def explain_event(self, event_type: str, event_data: dict[str, Any]) -> str:
        """Convert audit event to human-readable explanation."""
        explanations = {
            "STT": self._explain_stt,
            "EXTRACT": self._explain_extract,
            "TRIAGE": self._explain_triage,
            "GENERATE": self._explain_generate,
            "TTS": self._explain_tts,
        }

        handler = explanations.get(event_type)
        if handler:
            return handler(event_data)

        return f"Processing step: {event_type}"

    def _explain_stt(self, data: dict[str, Any]) -> str:
        model = data.get("model", "speech-to-text model")
        return f"Transcribed your audio using {model}."

    def _explain_extract(self, data: dict[str, Any]) -> str:
        model = data.get("model", "language model")
        symptoms = data.get("symptoms", [])
        if symptoms:
            symptom_list = ", ".join(symptoms[:3])
            if len(symptoms) > 3:
                symptom_list += f" and {len(symptoms) - 3} more"
            return f"Extracted key details using {model}: {symptom_list}."
        return f"Extracted key medical details using {model}."

    def _explain_triage(self, data: dict[str, Any]) -> str:
        acuity = data.get("acuity")
        red_flags = data.get("red_flags", [])
        escalate = data.get("escalate", False)

        parts = []
        if acuity:
            parts.append(f"Assessed urgency level: ESI-{acuity}")

        if red_flags:
            flag_names = [f.get("name", "unknown") if isinstance(f, dict) else str(f) for f in red_flags]
            parts.append(f"Safety check found concerns: {', '.join(flag_names)}")

        if escalate:
            parts.append("Decision: Escalate to human professional immediately.")
        else:
            parts.append("Decision: Continue assessment.")

        return " ".join(parts) if parts else "Performed triage assessment."

    def _explain_generate(self, data: dict[str, Any]) -> str:
        model = data.get("model", "language model")
        return f"Generated follow-up question using {model}."

    def _explain_tts(self, data: dict[str, Any]) -> str:
        model = data.get("model", "text-to-speech model")
        return f"Converted response to speech using {model}."

    def get_extraction_prompt(self) -> str:
        return EXTRACTION_SYSTEM_PROMPT

    def get_response_prompt(self) -> str:
        return FOLLOWUP_SYSTEM_PROMPT


# Singleton instance
medical_module = MedicalDomainModule()
