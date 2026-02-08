"""Tests for triage API endpoints using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient

from services.api.src.api.main import app
from services.api.src.api.routes import triage as triage_module


@pytest.fixture
def client(engine):
    """TestClient with overridden DB engine."""
    app.dependency_overrides[triage_module._engine] = lambda: engine
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Domains
# ---------------------------------------------------------------------------

class TestListDomains:
    def test_list_domains(self, client):
        res = client.get("/api/triage/domains")
        assert res.status_code == 200
        data = res.json()
        assert len(data["domains"]) == 3
        names = [d["name"] for d in data["domains"]]
        assert "medical" in names
        assert "sre" in names
        assert "crypto" in names


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

class TestCreateIncident:
    def test_create_medical_incident(self, client):
        res = client.post("/api/triage/incidents", json={"domain": "medical"})
        assert res.status_code == 200
        data = res.json()
        assert data["domain"] == "medical"
        assert data["status"] == "OPEN"
        assert data["mode"] == "chat"
        assert "id" in data

    def test_create_incident_with_voice_mode(self, client):
        res = client.post(
            "/api/triage/incidents", json={"domain": "medical", "mode": "voice"}
        )
        assert res.status_code == 200
        assert res.json()["mode"] == "voice"

    def test_create_incident_inactive_domain(self, client):
        res = client.post("/api/triage/incidents", json={"domain": "sre"})
        assert res.status_code == 400
        assert "not active" in res.json()["detail"]

    def test_create_incident_unknown_domain(self, client):
        res = client.post("/api/triage/incidents", json={"domain": "unknown"})
        assert res.status_code == 400

    def test_create_incident_invalid_mode(self, client):
        res = client.post(
            "/api/triage/incidents", json={"domain": "medical", "mode": "X"}
        )
        assert res.status_code == 400


class TestGetIncident:
    def test_get_existing_incident(self, client):
        create_res = client.post(
            "/api/triage/incidents", json={"domain": "medical"}
        )
        inc_id = create_res.json()["id"]

        res = client.get(f"/api/triage/incidents/{inc_id}")
        assert res.status_code == 200
        assert res.json()["id"] == inc_id

    def test_get_nonexistent_incident(self, client):
        res = client.get("/api/triage/incidents/does-not-exist")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

class TestSendMessage:
    def _create_incident(self, client) -> str:
        res = client.post(
            "/api/triage/incidents", json={"domain": "medical"}
        )
        return res.json()["id"]

    def test_send_message_returns_assistant_response(self, client):
        inc_id = self._create_incident(client)
        res = client.post(
            f"/api/triage/incidents/{inc_id}/messages",
            json={"content": "I have a headache"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["message"]["role"] == "patient"
        assert data["assistant_message"]["role"] == "assistant"
        assert data["assistant_message"]["content_text"] != ""

    def test_send_message_with_chest_pain_triggers_escalation(self, client):
        inc_id = self._create_incident(client)
        res = client.post(
            f"/api/triage/incidents/{inc_id}/messages",
            json={"content": "I have chest pain and shortness of breath"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["assessment"]["result_json"]["escalate"] is True
        assert data["assessment"]["result_json"]["acuity"] == 1

        # Incident should now be ESCALATED
        inc_res = client.get(f"/api/triage/incidents/{inc_id}")
        assert inc_res.json()["status"] == "ESCALATED"

    def test_send_message_minor_complaint(self, client):
        inc_id = self._create_incident(client)
        res = client.post(
            f"/api/triage/incidents/{inc_id}/messages",
            json={"content": "I have a runny nose"},
        )
        data = res.json()
        assert data["assessment"]["result_json"]["escalate"] is False
        assert data["assessment"]["result_json"]["acuity"] >= 4

    def test_send_message_nonexistent_incident(self, client):
        res = client.post(
            "/api/triage/incidents/fake-id/messages",
            json={"content": "hello"},
        )
        assert res.status_code == 404

    def test_send_message_creates_audit_events(self, client):
        inc_id = self._create_incident(client)
        client.post(
            f"/api/triage/incidents/{inc_id}/messages",
            json={"content": "I have a headache"},
        )

        timeline_res = client.get(f"/api/triage/incidents/{inc_id}/timeline")
        events = timeline_res.json()["events"]
        steps = [e["step"] for e in events]
        assert "EXTRACT" in steps
        assert "TRIAGE_RULES" in steps
        assert "RESPONSE_GENERATED" in steps


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

class TestTimeline:
    def test_empty_timeline(self, client):
        create_res = client.post(
            "/api/triage/incidents", json={"domain": "medical"}
        )
        inc_id = create_res.json()["id"]

        res = client.get(f"/api/triage/incidents/{inc_id}/timeline")
        assert res.status_code == 200
        assert res.json()["events"] == []
        assert res.json()["incident_id"] == inc_id

    def test_timeline_nonexistent_incident(self, client):
        res = client.get("/api/triage/incidents/fake-id/timeline")
        assert res.status_code == 404

    def test_timeline_after_messages(self, client):
        create_res = client.post(
            "/api/triage/incidents", json={"domain": "medical"}
        )
        inc_id = create_res.json()["id"]

        client.post(
            f"/api/triage/incidents/{inc_id}/messages",
            json={"content": "I have a headache and fever"},
        )

        res = client.get(f"/api/triage/incidents/{inc_id}/timeline")
        data = res.json()
        assert len(data["events"]) == 3
        # All events share the same trace_id
        trace_ids = set(e["trace_id"] for e in data["events"])
        assert len(trace_ids) == 1


# ---------------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------------

class TestVoiceEndpoint:
    def _create_incident(self, client) -> str:
        res = client.post(
            "/api/triage/incidents", json={"domain": "medical"}
        )
        return res.json()["id"]

    def test_voice_returns_transcript_and_response(self, client):
        inc_id = self._create_incident(client)
        res = client.post(
            f"/api/triage/incidents/{inc_id}/voice",
            files={"audio": ("test.webm", b"fake-audio-bytes", "audio/webm")},
        )
        assert res.status_code == 200
        data = res.json()
        assert "transcript" in data
        assert "response_text" in data
        # Note: transcript may be empty if STT fails with fake audio bytes

    def test_voice_nonexistent_incident(self, client):
        res = client.post(
            "/api/triage/incidents/fake-id/voice",
            files={"audio": ("test.webm", b"fake-audio", "audio/webm")},
        )
        assert res.status_code == 404
