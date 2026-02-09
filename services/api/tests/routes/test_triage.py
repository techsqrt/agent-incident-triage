"""Tests for triage API endpoints using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient

from services.api.src.api.main import app
from services.api.src.api.routes import triage as triage_module
from services.api.src.api.schemas.enums import Domain, IncidentMode, IncidentStatus, Severity


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
        assert Domain.MEDICAL.value in names
        assert Domain.SRE.value in names
        assert Domain.CRYPTO.value in names


# ---------------------------------------------------------------------------
# Incidents
# ---------------------------------------------------------------------------

class TestCreateIncident:
    def test_create_medical_incident(self, client):
        res = client.post("/api/triage/incidents", json={"domain": Domain.MEDICAL.value})
        assert res.status_code == 200
        data = res.json()
        assert data["domain"] == Domain.MEDICAL.value
        assert data["status"] == IncidentStatus.OPEN.value
        assert data["mode"] == IncidentMode.CHAT.value
        assert data["severity"] == Severity.UNASSIGNED.value
        assert "id" in data

    def test_create_incident_with_voice_mode(self, client):
        res = client.post(
            "/api/triage/incidents",
            json={"domain": Domain.MEDICAL.value, "mode": IncidentMode.VOICE.value}
        )
        assert res.status_code == 200
        assert res.json()["mode"] == IncidentMode.VOICE.value

    def test_create_incident_inactive_domain(self, client):
        res = client.post("/api/triage/incidents", json={"domain": Domain.SRE.value})
        assert res.status_code == 400
        assert "not active" in res.json()["detail"]

    def test_create_incident_unknown_domain(self, client):
        res = client.post("/api/triage/incidents", json={"domain": "unknown"})
        assert res.status_code == 422  # Pydantic validation error

    def test_create_incident_invalid_mode(self, client):
        res = client.post(
            "/api/triage/incidents",
            json={"domain": Domain.MEDICAL.value, "mode": "X"}
        )
        assert res.status_code == 422  # Pydantic validation error


class TestGetIncident:
    def test_get_existing_incident(self, client):
        create_res = client.post(
            "/api/triage/incidents", json={"domain": Domain.MEDICAL.value}
        )
        inc_id = create_res.json()["id"]

        res = client.get(f"/api/triage/incidents/{inc_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == inc_id
        assert data["severity"] == Severity.UNASSIGNED.value

    def test_get_nonexistent_incident(self, client):
        res = client.get("/api/triage/incidents/does-not-exist")
        assert res.status_code == 404


class TestListIncidents:
    def test_list_incidents_empty(self, client):
        res = client.get("/api/triage/incidents")
        assert res.status_code == 200
        data = res.json()
        assert "incidents" in data
        assert "total" in data

    def test_list_incidents_with_domain_filter(self, client):
        client.post("/api/triage/incidents", json={"domain": Domain.MEDICAL.value})

        res = client.get(f"/api/triage/incidents?domain={Domain.MEDICAL.value}")
        assert res.status_code == 200
        data = res.json()
        assert len(data["incidents"]) >= 1
        assert all(i["domain"] == Domain.MEDICAL.value for i in data["incidents"])

    def test_list_incidents_with_severity_filter(self, client):
        client.post("/api/triage/incidents", json={"domain": Domain.MEDICAL.value})

        res = client.get(f"/api/triage/incidents?severity={Severity.UNASSIGNED.value}")
        assert res.status_code == 200
        data = res.json()
        assert len(data["incidents"]) >= 1
        assert all(i["severity"] == Severity.UNASSIGNED.value for i in data["incidents"])

    def test_list_incidents_includes_severity(self, client):
        client.post("/api/triage/incidents", json={"domain": Domain.MEDICAL.value})

        res = client.get("/api/triage/incidents")
        assert res.status_code == 200
        data = res.json()
        assert len(data["incidents"]) >= 1
        for incident in data["incidents"]:
            assert "severity" in incident
            assert incident["severity"] in [s.value for s in Severity]

    def test_list_incidents_returns_total_count(self, client):
        # Create multiple incidents
        for _ in range(3):
            client.post("/api/triage/incidents", json={"domain": Domain.MEDICAL.value})

        res = client.get("/api/triage/incidents")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 3


class TestCloseReopenIncident:
    def _create_incident(self, client) -> str:
        res = client.post("/api/triage/incidents", json={"domain": Domain.MEDICAL.value})
        return res.json()["id"]

    def test_close_incident(self, client):
        inc_id = self._create_incident(client)

        res = client.post(f"/api/triage/incidents/{inc_id}/close")
        assert res.status_code == 200
        assert res.json()["status"] == IncidentStatus.CLOSED.value

    def test_close_already_closed_incident(self, client):
        inc_id = self._create_incident(client)

        client.post(f"/api/triage/incidents/{inc_id}/close")
        res = client.post(f"/api/triage/incidents/{inc_id}/close")
        assert res.status_code == 400
        assert "already closed" in res.json()["detail"]

    def test_reopen_closed_incident(self, client):
        inc_id = self._create_incident(client)

        client.post(f"/api/triage/incidents/{inc_id}/close")
        res = client.post(f"/api/triage/incidents/{inc_id}/reopen")

        assert res.status_code == 200
        assert res.json()["status"] == IncidentStatus.OPEN.value

    def test_reopen_open_incident_fails(self, client):
        inc_id = self._create_incident(client)

        res = client.post(f"/api/triage/incidents/{inc_id}/reopen")
        assert res.status_code == 400
        assert "closed" in res.json()["detail"].lower()

    def test_close_nonexistent_incident(self, client):
        res = client.post("/api/triage/incidents/fake-id/close")
        assert res.status_code == 404

    def test_reopen_nonexistent_incident(self, client):
        res = client.post("/api/triage/incidents/fake-id/reopen")
        assert res.status_code == 404

    def test_send_message_to_closed_incident_fails(self, client):
        inc_id = self._create_incident(client)
        client.post(f"/api/triage/incidents/{inc_id}/close")

        res = client.post(
            f"/api/triage/incidents/{inc_id}/messages",
            json={"content": "hello"},
        )
        assert res.status_code == 400
        assert "closed" in res.json()["detail"].lower()

    def test_closed_incident_response_includes_severity(self, client):
        inc_id = self._create_incident(client)

        res = client.post(f"/api/triage/incidents/{inc_id}/close")
        assert res.status_code == 200
        assert "severity" in res.json()

    def test_reopened_incident_response_includes_severity(self, client):
        inc_id = self._create_incident(client)
        client.post(f"/api/triage/incidents/{inc_id}/close")

        res = client.post(f"/api/triage/incidents/{inc_id}/reopen")
        assert res.status_code == 200
        assert "severity" in res.json()


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

class TestSendMessage:
    def _create_incident(self, client) -> str:
        res = client.post(
            "/api/triage/incidents", json={"domain": Domain.MEDICAL.value}
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

        inc_res = client.get(f"/api/triage/incidents/{inc_id}")
        assert inc_res.json()["status"] == IncidentStatus.ESCALATED.value

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
        # Updated step names for tool-call/tool-result pattern
        assert "TOOL_RESULT_EXTRACT" in steps
        assert "TOOL_RESULT_RULES" in steps
        assert "AGENT_DECISION" in steps

    def test_audit_events_include_conviction_scores(self, client):
        """Verify extraction audit event includes risk_signals with conviction scores."""
        inc_id = self._create_incident(client)
        # Send message with suicidal ideation to trigger conviction scoring
        client.post(
            f"/api/triage/incidents/{inc_id}/messages",
            json={"content": "I want to kill myself, I can't take it anymore"},
        )

        timeline_res = client.get(f"/api/triage/incidents/{inc_id}/timeline")
        events = timeline_res.json()["events"]

        # Find the TOOL_RESULT_EXTRACT event
        extract_event = next(
            (e for e in events if e["step"] == "TOOL_RESULT_EXTRACT"), None
        )
        assert extract_event is not None, "TOOL_RESULT_EXTRACT event not found"

        # Verify risk_signals exists in payload with conviction fields
        payload = extract_event.get("payload_json", {})
        risk_signals = payload.get("risk_signals", {})

        # Check that conviction fields exist
        assert "suicidal_ideation_conviction" in risk_signals, \
            f"suicidal_ideation_conviction missing from risk_signals: {risk_signals}"
        assert "chest_pain_conviction" in risk_signals
        assert "can_breathe_conviction" in risk_signals

        # For suicidal message, conviction should be high (deterministic fallback uses 0.9)
        assert risk_signals["suicidal_ideation_conviction"] > 0, \
            f"Expected suicidal conviction > 0 for suicidal message, got {risk_signals}"

    def test_audit_events_include_triggered_flags_with_thresholds(self, client):
        """Verify TOOL_RESULT_RULES includes triggered flags with conviction/threshold."""
        inc_id = self._create_incident(client)
        client.post(
            f"/api/triage/incidents/{inc_id}/messages",
            json={"content": "I have severe chest pain and can't breathe"},
        )

        timeline_res = client.get(f"/api/triage/incidents/{inc_id}/timeline")
        events = timeline_res.json()["events"]

        # Find the TOOL_RESULT_RULES event
        rules_event = next(
            (e for e in events if e["step"] == "TOOL_RESULT_RULES"), None
        )
        assert rules_event is not None, "TOOL_RESULT_RULES event not found"

        payload = rules_event.get("payload_json", {})
        triggered_flags = payload.get("triggered_risk_flags", [])

        # Should have triggered flags for chest pain and breathing
        assert len(triggered_flags) > 0, "Expected triggered risk flags"

        # Each triggered flag should have conviction and threshold
        for flag in triggered_flags:
            assert "flag_type" in flag, f"Missing flag_type in {flag}"
            assert "conviction" in flag, f"Missing conviction in {flag}"
            assert "threshold" in flag, f"Missing threshold in {flag}"
            assert flag["conviction"] >= flag["threshold"], \
                f"Conviction {flag['conviction']} should be >= threshold {flag['threshold']}"


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

class TestTimeline:
    def test_empty_timeline(self, client):
        create_res = client.post(
            "/api/triage/incidents", json={"domain": Domain.MEDICAL.value}
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
            "/api/triage/incidents", json={"domain": Domain.MEDICAL.value}
        )
        inc_id = create_res.json()["id"]

        client.post(
            f"/api/triage/incidents/{inc_id}/messages",
            json={"content": "I have a headache and fever"},
        )

        res = client.get(f"/api/triage/incidents/{inc_id}/timeline")
        data = res.json()
        # Audit events include: TOOL_CALL/RESULT for EXTRACT and RULES, plus AGENT_DECISION
        assert len(data["events"]) >= 3
        trace_ids = set(e["trace_id"] for e in data["events"])
        assert len(trace_ids) == 1


# ---------------------------------------------------------------------------
# Voice
# ---------------------------------------------------------------------------

class TestVoiceEndpoint:
    def _create_incident(self, client) -> str:
        res = client.post(
            "/api/triage/incidents", json={"domain": Domain.MEDICAL.value}
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

    def test_voice_nonexistent_incident(self, client):
        res = client.post(
            "/api/triage/incidents/fake-id/voice",
            files={"audio": ("test.webm", b"fake-audio", "audio/webm")},
        )
        assert res.status_code == 404
