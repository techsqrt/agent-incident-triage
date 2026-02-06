"""Redaction middleware for safe logging of sensitive data."""

import hashlib
import re
from typing import Any


# Patterns that should be redacted in audit logs
_SENSITIVE_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # SSN
    re.compile(r"\b\d{10,11}\b"),  # Phone numbers
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # Email
]

_SENSITIVE_KEYS = {"ssn", "social_security", "phone", "email", "address", "name",
                   "patient_name", "date_of_birth", "dob"}


def redact_value(value: str) -> str:
    """Hash a sensitive string value for safe storage."""
    return f"REDACTED:{hashlib.sha256(value.encode()).hexdigest()[:12]}"


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact sensitive fields from a dictionary."""
    result = {}
    for key, value in data.items():
        if key.lower() in _SENSITIVE_KEYS:
            result[key] = redact_value(str(value)) if value else None
        elif isinstance(value, dict):
            result[key] = redact_dict(value)
        elif isinstance(value, str):
            redacted = value
            for pattern in _SENSITIVE_PATTERNS:
                redacted = pattern.sub("[REDACTED]", redacted)
            result[key] = redacted
        else:
            result[key] = value
    return result
