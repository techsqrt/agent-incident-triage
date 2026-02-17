"""E2E escalation smoke tests via deterministic extraction + rules.

Each test sends a patient message through the full pipeline with the LLM
extractor mocked out, forcing the deterministic keyword-based path:
  API endpoint -> deterministic extraction -> deterministic rules -> escalation

This validates that the direct keyword detection rules correctly escalate
every critical category, independent of any LLM/probability-based extraction.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from services.api.src.api.main import app
from services.api.src.api.routes import triage as triage_module
from services.api.src.api.schemas.enums import IncidentStatus

pytestmark = pytest.mark.e2e


@pytest.fixture
def client(engine):
    """TestClient with overridden DB engine and LLM extraction disabled."""
    app.dependency_overrides[triage_module._engine] = lambda: engine
    # Force deterministic extraction by blanking only the API key
    with patch(
        "services.api.src.api.routes.triage.settings.openai_api_key", ""
    ):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


# Prompts use exact keywords from extract.py's deterministic detector.
# (id, prompt, max_acuity, expected_flag_type)
SCENARIOS = [
    (
        "chest_pain",
        "I'm having severe chest pain radiating to my left arm",
        2,
        "CHEST_PAIN",
    ),
    (
        "cannot_breathe",
        "I can't breathe, I'm gasping for air",
        2,
        "CANNOT_BREATHE",
    ),
    (
        "suicidal_ideation",
        "I want to kill myself, I can't take it anymore",
        2,
        "SUICIDAL_IDEATION",
    ),
    (
        "self_harm",
        "I want to hurt myself, I've been engaging in self-harm",
        2,
        "SELF_HARM",
    ),
    (
        "neuro_deficit",
        "My face is drooping and I have slurred speech",
        2,
        "NEURO_DEFICIT",
    ),
    (
        "uncontrolled_bleeding",
        "I have severe bleeding that won't stop",
        2,
        "BLEEDING_UNCONTROLLED",
    ),
    (
        "cardiac_arrest_esi1",
        "I think I'm having a heart attack and I can't breathe",
        1,
        "CANNOT_BREATHE",
    ),
]


@pytest.mark.parametrize(
    "name,prompt,max_acuity,expected_flag",
    SCENARIOS,
    ids=[s[0] for s in SCENARIOS],
)
def test_escalation(client, name, prompt, max_acuity, expected_flag):
    """Verify that deterministic keyword rules escalate critical messages."""
    # Create incident
    inc = client.post("/api/triage/incidents", json={"domain": "medical"})
    assert inc.status_code == 200
    inc_id = inc.json()["id"]

    # Send critical message
    res = client.post(
        f"/api/triage/incidents/{inc_id}/messages",
        json={"content": prompt},
    )
    assert res.status_code == 200
    data = res.json()

    result = data["assessment"]["result_json"]

    # Must escalate
    assert result["escalate"] is True, (
        f"[{name}] expected escalate=True, got {result}"
    )

    # Acuity must be at or below max
    assert result["acuity"] <= max_acuity, (
        f"[{name}] expected acuity <= {max_acuity}, got {result['acuity']}"
    )

    # Verify the expected flag was triggered by direct keyword detection,
    # not merely by a conviction score exceeding its threshold.
    # The deterministic extractor sets the boolean/tri-state signal value
    # directly (e.g. suicidal_ideation=True, chest_pain="yes", can_breathe="no")
    # which is stored as signal_value in triggered_risk_flags.
    triggered = result["triggered_risk_flags"]
    flag_types = [f["flag_type"] for f in triggered]
    assert expected_flag in flag_types, (
        f"[{name}] expected {expected_flag} in triggered_risk_flags, "
        f"got {flag_types}"
    )
    matched = next(f for f in triggered if f["flag_type"] == expected_flag)
    assert matched["signal_value"] in ("True", "yes", "no"), (
        f"[{name}] expected direct detection (True/yes/no), "
        f"got signal_value={matched['signal_value']}"
    )

    # Incident status must be ESCALATED
    inc_check = client.get(f"/api/triage/incidents/{inc_id}")
    assert inc_check.json()["status"] == IncidentStatus.ESCALATED.value, (
        f"[{name}] expected status ESCALATED, got {inc_check.json()['status']}"
    )
