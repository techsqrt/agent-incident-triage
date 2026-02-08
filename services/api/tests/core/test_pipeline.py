"""Tests for the medical voice pipeline with mocked adapters."""

import pytest
from sqlalchemy import create_engine, StaticPool

from services.api.src.api.core.pipeline import run_voice_pipeline
from services.api.src.api.db.models import metadata
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
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(eng)
    return eng


@pytest.fixture
def incident_id(engine):
    repo = IncidentRepository(engine)
    row = repo.create(domain="medical", mode="B")
    return row["id"]


# -- Tests -------------------------------------------------------------------

class TestVoicePipeline:
    def test_pipeline_returns_transcript_and_response(self, engine, incident_id):
        result = run_voice_pipeline(
            incident_id=incident_id,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=engine,
            stt_fn=mock_stt,
            extract_fn=mock_extract,
            generate_fn=mock_generate,
            tts_fn=mock_tts,
        )

        assert result.transcript == "I have a headache and fever"
        assert result.response_text == "How long have you had these symptoms?"
        assert result.audio_base64 == "bW9jaw=="
        assert result.trace_id != ""

    def test_pipeline_creates_audit_events(self, engine, incident_id):
        result = run_voice_pipeline(
            incident_id=incident_id,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=engine,
            stt_fn=mock_stt,
            extract_fn=mock_extract,
            generate_fn=mock_generate,
            tts_fn=mock_tts,
        )

        audit_repo = AuditEventRepository(engine)
        events = audit_repo.list_by_incident(incident_id)

        steps = [e["step"] for e in events]
        assert "STT" in steps
        assert "EXTRACT" in steps
        assert "TRIAGE_RULES" in steps
        assert "GENERATE" in steps
        assert "TTS" in steps

        # All events share the same trace_id
        trace_ids = set(e["trace_id"] for e in events)
        assert len(trace_ids) == 1
        assert result.trace_id in trace_ids

    def test_pipeline_persists_messages(self, engine, incident_id):
        run_voice_pipeline(
            incident_id=incident_id,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=engine,
            stt_fn=mock_stt,
            extract_fn=mock_extract,
            generate_fn=mock_generate,
            tts_fn=mock_tts,
        )

        msg_repo = MessageRepository(engine)
        messages = msg_repo.list_by_incident(incident_id)

        assert len(messages) == 2
        assert messages[0]["role"] == "patient"
        assert messages[1]["role"] == "assistant"

    def test_pipeline_creates_assessment(self, engine, incident_id):
        result = run_voice_pipeline(
            incident_id=incident_id,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=engine,
            stt_fn=mock_stt,
            extract_fn=mock_extract,
            generate_fn=mock_generate,
            tts_fn=mock_tts,
        )

        assert result.assessment_row is not None
        assert result.assessment_row["domain"] == "medical"

    def test_pipeline_escalates_critical(self, engine, incident_id):
        run_voice_pipeline(
            incident_id=incident_id,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=engine,
            stt_fn=mock_stt_critical,
            extract_fn=mock_extract_critical,
            generate_fn=mock_generate,
            tts_fn=mock_tts,
        )

        incident_repo = IncidentRepository(engine)
        incident = incident_repo.get(incident_id)
        assert incident["status"] == "ESCALATED"

    def test_pipeline_escalation_skips_generate(self, engine, incident_id):
        """When case is critical, pipeline should NOT call generate_fn
        and should return a fixed escalation message instead."""
        generate_called = False

        def mock_generate_spy(extraction_dict):
            nonlocal generate_called
            generate_called = True
            return "follow-up question?", {}

        result = run_voice_pipeline(
            incident_id=incident_id,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=engine,
            stt_fn=mock_stt_critical,
            extract_fn=mock_extract_critical,
            generate_fn=mock_generate_spy,
            tts_fn=mock_tts,
        )

        assert generate_called is False
        assert "escalating" in result.response_text.lower()
        assert "immediate medical attention" in result.response_text.lower()

    def test_pipeline_escalation_response_text(self, engine):
        """Escalated cases get a fixed response, not an LLM-generated one."""
        repo = IncidentRepository(engine)
        row = repo.create(domain="medical", mode="B")
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
            engine=engine,
            stt_fn=mock_stt,
            extract_fn=mock_extract_dying,
            generate_fn=mock_generate,
            tts_fn=mock_tts,
        )

        assert result.assessment_row is not None
        assert "escalating" in result.response_text.lower()

    def test_pipeline_audit_has_latency(self, engine, incident_id):
        run_voice_pipeline(
            incident_id=incident_id,
            audio_bytes=b"fake-audio",
            filename="test.webm",
            engine=engine,
            stt_fn=mock_stt,
            extract_fn=mock_extract,
            generate_fn=mock_generate,
            tts_fn=mock_tts,
        )

        audit_repo = AuditEventRepository(engine)
        events = audit_repo.list_by_incident(incident_id)

        for event in events:
            assert event["latency_ms"] is not None
            assert event["latency_ms"] >= 0
