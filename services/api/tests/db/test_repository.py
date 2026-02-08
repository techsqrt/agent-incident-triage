"""Unit tests for repository layer using mocks.

For PostgreSQL constraint testing, see tests/integration/test_db_constraints.py
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


class TestIncidentRepositoryUnit:
    """Unit tests for IncidentRepository logic (mocked DB)."""

    def test_create_returns_expected_structure(self):
        """Verify create() returns dict with required fields."""
        from services.api.src.api.db.repository import IncidentRepository

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        repo = IncidentRepository(mock_engine)

        with patch('services.api.src.api.db.repository._new_id', return_value='test-id'):
            with patch('services.api.src.api.db.repository._now', return_value=datetime(2024, 1, 1, tzinfo=timezone.utc)):
                row = repo.create(domain="medical", mode="chat")

        assert row["id"] == "test-id"
        assert row["domain"] == "medical"
        assert row["mode"] == "chat"
        assert row["status"] == "OPEN"
        assert "history" in row
        assert row["history"]["interactions"][0]["type"] == "system_created"

    def test_create_default_mode_is_chat(self):
        """Default mode should be 'chat'."""
        from services.api.src.api.db.repository import IncidentRepository

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        repo = IncidentRepository(mock_engine)
        row = repo.create(domain="medical")

        assert row["mode"] == "chat"


class TestMessageRepositoryUnit:
    """Unit tests for MessageRepository."""

    def test_create_returns_expected_structure(self):
        from services.api.src.api.db.repository import MessageRepository

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        repo = MessageRepository(mock_engine)

        with patch('services.api.src.api.db.repository._new_id', return_value='msg-id'):
            row = repo.create("inc-id", "patient", "Hello")

        assert row["id"] == "msg-id"
        assert row["incident_id"] == "inc-id"
        assert row["role"] == "patient"
        assert row["content_text"] == "Hello"


class TestAssessmentRepositoryUnit:
    """Unit tests for AssessmentRepository."""

    def test_create_serializes_json(self):
        from services.api.src.api.db.repository import AssessmentRepository

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        repo = AssessmentRepository(mock_engine)

        with patch('services.api.src.api.db.repository._new_id', return_value='assess-id'):
            row = repo.create("inc-id", "medical", {"acuity": 3})

        # Verify JSON was serialized
        call_args = mock_conn.execute.call_args
        values = call_args[0][0].compile().params
        assert json.loads(values["result_json"]) == {"acuity": 3}


class TestAuditEventRepositoryUnit:
    """Unit tests for AuditEventRepository."""

    def test_append_creates_event(self):
        from services.api.src.api.db.repository import AuditEventRepository

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.begin.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_engine.begin.return_value.__exit__ = MagicMock(return_value=False)

        repo = AuditEventRepository(mock_engine)

        with patch('services.api.src.api.db.repository._new_id', return_value='event-id'):
            row = repo.append(
                incident_id="inc-id",
                trace_id="trace-1",
                step="TEST",
                latency_ms=100,
            )

        assert row["id"] == "event-id"
        assert row["step"] == "TEST"
        assert row["latency_ms"] == 100
