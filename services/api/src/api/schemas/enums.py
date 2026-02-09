"""Enums for triage API."""

from enum import Enum


class IncidentStatus(str, Enum):
    """Possible states for a triage incident."""
    OPEN = "OPEN"
    TRIAGE_READY = "TRIAGE_READY"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class IncidentMode(str, Enum):
    """Interaction mode for an incident."""
    CHAT = "chat"
    VOICE = "voice"


class Domain(str, Enum):
    """Available triage domains."""
    MEDICAL = "medical"
    SRE = "sre"
    CRYPTO = "crypto"


class Severity(str, Enum):
    """ESI-based severity level for an incident."""
    UNASSIGNED = "UNASSIGNED"  # Not yet classified
    ESI_1 = "ESI-1"            # Immediate life threat (unresponsive, cardiac arrest)
    ESI_2 = "ESI-2"            # High risk (confused, severe pain 8+, multiple red flags)
    ESI_3 = "ESI-3"            # Moderate (single red flag, moderate pain, abnormal vitals)
    ESI_4 = "ESI-4"            # Mild (some symptoms but nothing alarming)
    ESI_5 = "ESI-5"            # Minor (simple complaint, no concerning findings)
