"""Integration tests for PostgreSQL database constraints.

These tests verify that CHECK constraints and other PostgreSQL-specific
behavior works correctly. Run with: pytest -m integration
"""

import pytest

from services.api.src.api.db.repository import (
    IncidentRepository,
    MessageRepository,
    AssessmentRepository,
    AuditEventRepository,
)


pytestmark = pytest.mark.integration


class TestIncidentConstraints:
    """Test PostgreSQL CHECK constraints on incidents table."""

    def test_mode_constraint_accepts_chat(self, pg_engine):
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="medical", mode="chat")
        assert row["mode"] == "chat"

    def test_mode_constraint_accepts_voice(self, pg_engine):
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="medical", mode="voice")
        assert row["mode"] == "voice"

    def test_mode_constraint_rejects_invalid(self, pg_engine):
        """PostgreSQL CHECK constraint rejects invalid mode values."""
        repo = IncidentRepository(pg_engine)
        with pytest.raises(Exception) as exc_info:
            repo.create(domain="medical", mode="invalid")
        assert "violates check constraint" in str(exc_info.value).lower()

    def test_mode_constraint_rejects_old_values(self, pg_engine):
        """Old A/B mode values are rejected."""
        repo = IncidentRepository(pg_engine)
        with pytest.raises(Exception):
            repo.create(domain="medical", mode="A")
        with pytest.raises(Exception):
            repo.create(domain="medical", mode="B")

    def test_domain_constraint_accepts_valid(self, pg_engine):
        repo = IncidentRepository(pg_engine)
        for domain in ["medical", "sre", "crypto"]:
            row = repo.create(domain=domain)
            assert row["domain"] == domain

    def test_domain_constraint_rejects_invalid(self, pg_engine):
        repo = IncidentRepository(pg_engine)
        with pytest.raises(Exception) as exc_info:
            repo.create(domain="unknown")
        assert "violates check constraint" in str(exc_info.value).lower()

    def test_status_constraint_accepts_valid(self, pg_engine):
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="medical")
        for status in ["OPEN", "TRIAGE_READY", "ESCALATED", "CLOSED"]:
            repo.update_status(row["id"], status)
            fetched = repo.get(row["id"])
            assert fetched["status"] == status

    def test_status_constraint_rejects_invalid(self, pg_engine):
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="medical")
        with pytest.raises(Exception) as exc_info:
            repo.update_status(row["id"], "INVALID_STATUS")
        assert "violates check constraint" in str(exc_info.value).lower()


class TestRepositoryIntegration:
    """Integration tests for repository operations with real PostgreSQL."""

    def test_incident_create_and_get(self, pg_engine):
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="medical", mode="chat")

        fetched = repo.get(row["id"])
        assert fetched is not None
        assert fetched["domain"] == "medical"
        assert fetched["mode"] == "chat"
        assert fetched["status"] == "OPEN"

    def test_incident_history_jsonb(self, pg_engine):
        """Test JSONB operations work correctly."""
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="medical")

        # Append interactions
        repo.append_interaction(row["id"], {
            "type": "user_sent",
            "content": "Hello",
        })
        repo.append_interaction(row["id"], {
            "type": "agent_responded",
            "content": "Hi there",
        })

        fetched = repo.get(row["id"])
        assert len(fetched["history"]["interactions"]) == 3  # 1 system_created + 2

    def test_incident_diagnostic_jsonb(self, pg_engine):
        """Test diagnostic JSONB updates merge correctly."""
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="medical")

        repo.update_diagnostic(row["id"], {"model": "gpt-4"})
        repo.update_diagnostic(row["id"], {"tokens": 500})

        fetched = repo.get(row["id"])
        assert fetched["diagnostic"]["model"] == "gpt-4"
        assert fetched["diagnostic"]["tokens"] == 500

    def test_message_foreign_key(self, pg_engine):
        """Test foreign key relationships work."""
        inc_repo = IncidentRepository(pg_engine)
        msg_repo = MessageRepository(pg_engine)

        inc = inc_repo.create(domain="medical")
        msg_repo.create(inc["id"], "patient", "Hello")

        messages = msg_repo.list_by_incident(inc["id"])
        assert len(messages) == 1

    def test_assessment_foreign_key(self, pg_engine):
        inc_repo = IncidentRepository(pg_engine)
        assess_repo = AssessmentRepository(pg_engine)

        inc = inc_repo.create(domain="medical")
        assess_repo.create(inc["id"], "medical", {"acuity": 3})

        latest = assess_repo.get_latest(inc["id"])
        assert latest["result_json"]["acuity"] == 3

    def test_audit_events(self, pg_engine):
        inc_repo = IncidentRepository(pg_engine)
        audit_repo = AuditEventRepository(pg_engine)

        inc = inc_repo.create(domain="medical")
        audit_repo.append(
            incident_id=inc["id"],
            trace_id="trace-1",
            step="TEST",
            payload_json={"test": True},
            latency_ms=100,
        )

        events = audit_repo.list_by_incident(inc["id"])
        assert len(events) == 1
        assert events[0]["step"] == "TEST"
