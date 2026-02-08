"""Integration tests for the medical voice pipeline.

Uses mocked adapters (STT, TTS, LLM) but real PostgreSQL database.
Run with: pytest -m integration
"""

import pytest

pytestmark = pytest.mark.integration

from services.api.src.api.core.pipeline import run_voice_pipeline
from services.api.src.api.db.repository import (
    AuditEventRepository,
    IncidentRepository,
    MessageRepository,
)
from services.api.src.api.domains.medical.schemas import MedicalExtraction


# -- Mock adapters -----------------------------------------------------------

class MockSTTResult:
    def __init__(self, text):
        self.text = text
        self.model = "mock-stt"


class MockTTSResult:
    def __init__(self):
        self.audio_base64 = "bW9jaw=="
        self.model = "mock-tts"


def mock_stt(audio_bytes, filename="audio.webm"):
    return MockSTTResult("I have a headache and fever")


def mock_stt_critical(audio_bytes, filename="audio.webm"):
    return MockSTTResult("I have chest pain and shortness of breath")


def mock_extract(text):
    return MedicalExtraction(
        chief_complaint=text[:200],
        symptoms=["headache", "fever"],
        pain_scale=5,
    )


def mock_extract_critical(text):
    return MedicalExtraction(
        chief_complaint=text[:200],
        symptoms=["chest pain", "shortness of breath"],
        pain_scale=9,
    )


def mock_generate(extraction_dict):
    return "How long have you had these symptoms?", {}


def mock_tts(text):
    return MockTTSResult()


# -- Fixtures ----------------------------------------------------------------

@pytest.fixture
def incident_id(pg_engine):
    repo = IncidentRepository(pg_engine)
    row = repo.create(domain="medical", mode="chat")
    return row["id"]


# -- Tests -------------------------------------------------------------------

class TestVoicePipeline:
    def test_pipeline_returns_transcript_and_response(self, pg_engine, incident_id):
        result = run_voice_pipeline(
            incident_id=incident_id,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=pg_engine,
            stt_fn=mock_stt,
            extract_fn=mock_extract,
            generate_fn=mock_generate,
            tts_fn=mock_tts,
        )

        assert result.transcript == "I have a headache and fever"
        assert result.response_text == "How long have you had these symptoms?"
        assert result.audio_base64 == "bW9jaw=="
        assert result.trace_id != ""

    def test_pipeline_creates_audit_events(self, pg_engine, incident_id):
        run_voice_pipeline(
            incident_id=incident_id,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=pg_engine,
            stt_fn=mock_stt,
            extract_fn=mock_extract,
            generate_fn=mock_generate,
            tts_fn=mock_tts,
        )

        repo = AuditEventRepository(pg_engine)
        events = repo.list_by_incident(incident_id)
        steps = [e["step"] for e in events]

        assert "STT" in steps
        assert "EXTRACT" in steps
        assert "TRIAGE_RULES" in steps
        assert "GENERATE" in steps
        assert "TTS" in steps

    def test_pipeline_persists_messages(self, pg_engine, incident_id):
        run_voice_pipeline(
            incident_id=incident_id,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=pg_engine,
            stt_fn=mock_stt,
            extract_fn=mock_extract,
            generate_fn=mock_generate,
            tts_fn=mock_tts,
        )

        repo = MessageRepository(pg_engine)
        messages = repo.list_by_incident(incident_id)

        assert len(messages) == 2
        assert messages[0]["role"] == "patient"
        assert "headache" in messages[0]["content_text"].lower()
        assert messages[1]["role"] == "assistant"

    def test_pipeline_creates_assessment(self, pg_engine, incident_id):
        result = run_voice_pipeline(
            incident_id=incident_id,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=pg_engine,
            stt_fn=mock_stt,
            extract_fn=mock_extract,
            generate_fn=mock_generate,
            tts_fn=mock_tts,
        )

        assert result.assessment_row is not None
        # result_json contains the actual assessment data
        import json
        assessment = json.loads(result.assessment_row["result_json"]) if isinstance(result.assessment_row["result_json"], str) else result.assessment_row["result_json"]
        assert "acuity" in assessment

    def test_pipeline_escalates_critical(self, pg_engine, incident_id):
        result = run_voice_pipeline(
            incident_id=incident_id,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=pg_engine,
            stt_fn=mock_stt_critical,
            extract_fn=mock_extract_critical,
            generate_fn=mock_generate,
            tts_fn=mock_tts,
        )

        assert result.assessment_row is not None
        import json
        assessment = json.loads(result.assessment_row["result_json"]) if isinstance(result.assessment_row["result_json"], str) else result.assessment_row["result_json"]
        assert assessment["escalate"] is True
        assert assessment["acuity"] == 1

        # Check incident status was updated
        repo = IncidentRepository(pg_engine)
        incident = repo.get(incident_id)
        assert incident["status"] == "ESCALATED"

    def test_pipeline_escalation_skips_generate(self, pg_engine, incident_id):
        generate_called = False

        def tracking_generate(extraction_dict):
            nonlocal generate_called
            generate_called = True
            return "Should not be called", {}

        result = run_voice_pipeline(
            incident_id=incident_id,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=pg_engine,
            stt_fn=mock_stt_critical,
            extract_fn=mock_extract_critical,
            generate_fn=tracking_generate,
            tts_fn=mock_tts,
        )

        assert generate_called is False
        assert "escalating" in result.response_text.lower()
        assert "immediate medical attention" in result.response_text.lower()

    def test_pipeline_escalation_response_text(self, pg_engine):
        """Escalated cases get a fixed response, not an LLM-generated one."""
        repo = IncidentRepository(pg_engine)
        row = repo.create(domain="medical", mode="chat")
        iid = row["id"]

        def mock_extract_dying(text):
            return MedicalExtraction(
                chief_complaint="I'm dying",
                symptoms=["dying"],
            )

        result = run_voice_pipeline(
            incident_id=iid,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=pg_engine,
            stt_fn=lambda *a, **kw: MockSTTResult("I'm dying"),
            extract_fn=mock_extract_dying,
            generate_fn=mock_generate,
            tts_fn=mock_tts,
        )

        import json
        assessment = json.loads(result.assessment_row["result_json"]) if isinstance(result.assessment_row["result_json"], str) else result.assessment_row["result_json"]
        assert assessment["escalate"] is True
        assert "escalating" in result.response_text.lower()

    def test_pipeline_audit_has_latency(self, pg_engine, incident_id):
        run_voice_pipeline(
            incident_id=incident_id,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=pg_engine,
            stt_fn=mock_stt,
            extract_fn=mock_extract,
            generate_fn=mock_generate,
            tts_fn=mock_tts,
        )

        repo = AuditEventRepository(pg_engine)
        events = repo.list_by_incident(incident_id)

        for event in events:
            assert event["latency_ms"] is not None
            assert event["latency_ms"] >= 0
