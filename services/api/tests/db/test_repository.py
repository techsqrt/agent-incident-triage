"""Tests for triage repositories using in-memory SQLite."""

import pytest
from sqlalchemy import create_engine

from services.api.src.api.db.models import metadata
from services.api.src.api.db.repository import (
    IncidentRepository,
    MessageRepository,
    AssessmentRepository,
    AuditEventRepository,
)


@pytest.fixture
def engine():
    """Create a fresh in-memory SQLite database for each test."""
    eng = create_engine("sqlite:///:memory:")
    metadata.create_all(eng)
    return eng


@pytest.fixture
def incident_repo(engine):
    return IncidentRepository(engine)


@pytest.fixture
def message_repo(engine):
    return MessageRepository(engine)


@pytest.fixture
def assessment_repo(engine):
    return AssessmentRepository(engine)


@pytest.fixture
def audit_repo(engine):
    return AuditEventRepository(engine)


class TestIncidentRepository:
    def test_create_and_get(self, incident_repo):
        row = incident_repo.create(domain="medical", mode="B")
        assert row["domain"] == "medical"
        assert row["status"] == "OPEN"
        assert row["mode"] == "B"

        fetched = incident_repo.get(row["id"])
        assert fetched is not None
        assert fetched["id"] == row["id"]

    def test_get_nonexistent(self, incident_repo):
        assert incident_repo.get("does-not-exist") is None

    def test_update_status(self, incident_repo):
        row = incident_repo.create(domain="medical")
        incident_repo.update_status(row["id"], "ESCALATED")
        fetched = incident_repo.get(row["id"])
        assert fetched["status"] == "ESCALATED"

    def test_list_by_domain(self, incident_repo):
        incident_repo.create(domain="medical")
        incident_repo.create(domain="medical")
        incident_repo.create(domain="sre")

        medical = incident_repo.list_by_domain("medical")
        assert len(medical) == 2

        sre = incident_repo.list_by_domain("sre")
        assert len(sre) == 1


class TestMessageRepository:
    def test_create_and_list(self, incident_repo, message_repo):
        inc = incident_repo.create(domain="medical")

        message_repo.create(inc["id"], "patient", "I have chest pain")
        message_repo.create(inc["id"], "assistant", "Can you describe the pain?")

        messages = message_repo.list_by_incident(inc["id"])
        assert len(messages) == 2
        assert messages[0]["role"] == "patient"
        assert messages[1]["role"] == "assistant"


class TestAssessmentRepository:
    def test_create_and_get_latest(self, incident_repo, assessment_repo):
        inc = incident_repo.create(domain="medical")

        assessment_repo.create(inc["id"], "medical", {"acuity": 3})
        assessment_repo.create(inc["id"], "medical", {"acuity": 2, "escalate": True})

        latest = assessment_repo.get_latest(inc["id"])
        assert latest is not None
        assert latest["result_json"]["acuity"] == 2
        assert latest["result_json"]["escalate"] is True

    def test_get_latest_empty(self, incident_repo, assessment_repo):
        inc = incident_repo.create(domain="medical")
        assert assessment_repo.get_latest(inc["id"]) is None


class TestAuditEventRepository:
    def test_append_and_list(self, incident_repo, audit_repo):
        inc = incident_repo.create(domain="medical")

        audit_repo.append(
            incident_id=inc["id"],
            trace_id="trace-001",
            step="STT",
            payload_json={"duration_s": 3.2},
            latency_ms=450,
            model_used="gpt-4o-mini-transcribe",
        )
        audit_repo.append(
            incident_id=inc["id"],
            trace_id="trace-001",
            step="EXTRACT",
            payload_json={"fields_extracted": 5},
            latency_ms=320,
            model_used="gpt-4o-mini",
            token_usage_json={"prompt_tokens": 100, "completion_tokens": 50},
        )

        events = audit_repo.list_by_incident(inc["id"])
        assert len(events) == 2
        assert events[0]["step"] == "STT"
        assert events[0]["payload_json"]["duration_s"] == 3.2
        assert events[1]["token_usage_json"]["prompt_tokens"] == 100
