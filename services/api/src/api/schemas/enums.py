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
