"""Tests for PostgreSQL CHECK constraints.

These tests verify that the database properly enforces constraints.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from services.api.src.api.db.repository import IncidentRepository


class TestIncidentConstraints:
    """Test CHECK constraints on triage_incidents table."""

    def test_valid_mode_chat_accepted(self, pg_engine):
        """Mode 'chat' should be accepted."""
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="medical", mode="chat")
        assert row["mode"] == "chat"

    def test_valid_mode_voice_accepted(self, pg_engine):
        """Mode 'voice' should be accepted."""
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="medical", mode="voice")
        assert row["mode"] == "voice"

    def test_invalid_mode_rejected(self, pg_engine):
        """Invalid mode values should be rejected by CHECK constraint."""
        repo = IncidentRepository(pg_engine)
        with pytest.raises(IntegrityError) as exc_info:
            repo.create(domain="medical", mode="invalid")
        assert "check" in str(exc_info.value).lower()

    def test_old_mode_a_rejected(self, pg_engine):
        """Old mode 'A' should be rejected (was removed in migration)."""
        repo = IncidentRepository(pg_engine)
        with pytest.raises(IntegrityError) as exc_info:
            repo.create(domain="medical", mode="A")
        assert "check" in str(exc_info.value).lower()

    def test_old_mode_b_rejected(self, pg_engine):
        """Old mode 'B' should be rejected (was removed in migration)."""
        repo = IncidentRepository(pg_engine)
        with pytest.raises(IntegrityError) as exc_info:
            repo.create(domain="medical", mode="B")
        assert "check" in str(exc_info.value).lower()

    def test_valid_domain_medical(self, pg_engine):
        """Domain 'medical' should be accepted."""
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="medical")
        assert row["domain"] == "medical"

    def test_valid_domain_sre(self, pg_engine):
        """Domain 'sre' should be accepted."""
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="sre")
        assert row["domain"] == "sre"

    def test_valid_domain_crypto(self, pg_engine):
        """Domain 'crypto' should be accepted."""
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="crypto")
        assert row["domain"] == "crypto"

    def test_invalid_domain_rejected(self, pg_engine):
        """Invalid domain values should be rejected by CHECK constraint."""
        repo = IncidentRepository(pg_engine)
        with pytest.raises(IntegrityError) as exc_info:
            repo.create(domain="unknown")
        assert "check" in str(exc_info.value).lower()

    def test_valid_status_transitions(self, pg_engine):
        """Valid status values should be accepted."""
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="medical")
        assert row["status"] == "OPEN"

        repo.update_status(row["id"], "TRIAGE_READY")
        updated = repo.get(row["id"])
        assert updated["status"] == "TRIAGE_READY"

        repo.update_status(row["id"], "ESCALATED")
        updated = repo.get(row["id"])
        assert updated["status"] == "ESCALATED"

        repo.update_status(row["id"], "CLOSED")
        updated = repo.get(row["id"])
        assert updated["status"] == "CLOSED"

    def test_invalid_status_rejected(self, pg_engine):
        """Invalid status values should be rejected by CHECK constraint."""
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="medical")

        with pytest.raises(IntegrityError) as exc_info:
            repo.update_status(row["id"], "INVALID_STATUS")
        assert "check" in str(exc_info.value).lower()
