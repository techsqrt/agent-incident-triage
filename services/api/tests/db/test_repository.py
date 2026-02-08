"""Tests for triage repositories using PostgreSQL."""

import pytest

from services.api.src.api.db.repository import (
    IncidentRepository,
    MessageRepository,
    AssessmentRepository,
    AuditEventRepository,
)


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
        row = incident_repo.create(domain="medical", mode="chat")
        assert row["domain"] == "medical"
        assert row["status"] == "OPEN"
        assert row["mode"] == "chat"

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

    def test_create_with_history(self, incident_repo):
        """Incident should have initial system_created interaction."""
        row = incident_repo.create(domain="medical", mode="voice")
        assert "history" in row
        assert "interactions" in row["history"]
        assert len(row["history"]["interactions"]) == 1
        assert row["history"]["interactions"][0]["type"] == "system_created"
        assert row["history"]["interactions"][0]["domain"] == "medical"
        assert row["history"]["interactions"][0]["mode"] == "voice"

    def test_append_interaction(self, incident_repo):
        """Append interactions to history."""
        row = incident_repo.create(domain="medical")

        incident_repo.append_interaction(row["id"], {
            "type": "user_sent",
            "ts": "2024-01-15T10:30:00Z",
            "content": "I have a headache",
            "mode": "chat",
        })
        incident_repo.append_interaction(row["id"], {
            "type": "agent_responded",
            "ts": "2024-01-15T10:30:02Z",
            "content": "Can you describe the pain?",
            "model": "gpt-4o",
            "latency_ms": 350,
        })

        fetched = incident_repo.get(row["id"])
        assert len(fetched["history"]["interactions"]) == 3  # 1 system_created + 2 new
        assert fetched["history"]["interactions"][1]["type"] == "user_sent"
        assert fetched["history"]["interactions"][2]["type"] == "agent_responded"

    def test_set_escalated(self, incident_repo):
        """Set escalation with timestamp."""
        row = incident_repo.create(domain="medical")
        assert row["ts_escalated"] is None

        incident_repo.set_escalated(row["id"])

        fetched = incident_repo.get(row["id"])
        assert fetched["status"] == "ESCALATED"
        assert fetched["ts_escalated"] is not None

    def test_update_diagnostic(self, incident_repo):
        """Update diagnostic metadata."""
        row = incident_repo.create(domain="medical")
        assert row["diagnostic"] == {}

        incident_repo.update_diagnostic(row["id"], {
            "model_extraction": "gpt-4o",
            "total_tokens_input": 500,
        })
        incident_repo.update_diagnostic(row["id"], {
            "total_tokens_output": 200,
        })

        fetched = incident_repo.get(row["id"])
        assert fetched["diagnostic"]["model_extraction"] == "gpt-4o"
        assert fetched["diagnostic"]["total_tokens_input"] == 500
        assert fetched["diagnostic"]["total_tokens_output"] == 200

    def test_list_all_with_filters(self, incident_repo):
        """List incidents with domain and status filters."""
        incident_repo.create(domain="medical")
        incident_repo.create(domain="medical")
        incident_repo.create(domain="sre")
        inc = incident_repo.create(domain="medical")
        incident_repo.update_status(inc["id"], "CLOSED")

        # All incidents
        all_inc = incident_repo.list_all()
        assert len(all_inc) == 4

        # Filter by domain
        medical = incident_repo.list_all(domain="medical")
        assert len(medical) == 3

        # Filter by status
        closed = incident_repo.list_all(status="CLOSED")
        assert len(closed) == 1

        # Filter by both
        open_sre = incident_repo.list_all(domain="sre", status="OPEN")
        assert len(open_sre) == 1


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
