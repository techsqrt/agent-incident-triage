"""Tests for redaction middleware."""

from services.api.src.api.core.redaction import redact_dict, redact_value


def test_redact_value_returns_hash():
    result = redact_value("sensitive-data")
    assert result.startswith("REDACTED:")
    assert len(result) > 10


def test_redact_value_deterministic():
    assert redact_value("test") == redact_value("test")


def test_redact_dict_sensitive_keys():
    data = {
        "patient_name": "John Doe",
        "chief_complaint": "chest pain",
        "ssn": "123-45-6789",
    }
    result = redact_dict(data)
    assert result["patient_name"].startswith("REDACTED:")
    assert result["ssn"].startswith("REDACTED:")
    assert result["chief_complaint"] == "chest pain"


def test_redact_dict_nested():
    data = {
        "patient": {
            "name": "Jane Doe",
            "symptoms": "headache",
        },
    }
    result = redact_dict(data)
    assert result["patient"]["name"].startswith("REDACTED:")
    assert result["patient"]["symptoms"] == "headache"


def test_redact_dict_ssn_pattern_in_text():
    data = {
        "note": "Patient SSN is 123-45-6789 on file",
    }
    result = redact_dict(data)
    assert "123-45-6789" not in result["note"]
    assert "[REDACTED]" in result["note"]
