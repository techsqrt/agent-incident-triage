"""E2E conviction-based escalation tests via real LLM extraction.

Each test sends a synonymous patient message (avoiding the exact flagged
keywords used by deterministic detection) through the FULL pipeline
including the OpenAI LLM:

  API endpoint -> LLM extraction (real GPT call) -> deterministic rules -> escalation

This validates that the LLM correctly identifies critical risk signals from
natural language and assigns conviction scores high enough to trigger the
threshold-based escalation rules.

Requires OPENAI_API_KEY — skipped when the key is not set.
Runs in CI on push to main/master via the e2e job.
"""

import os

import pytest
from fastapi.testclient import TestClient

from services.api.src.api.main import app
from services.api.src.api.routes import triage as triage_module
from services.api.src.api.schemas.enums import IncidentStatus

_has_key = bool(os.environ.get("OPENAI_API_KEY"))

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not _has_key, reason="OPENAI_API_KEY not set"),
]


@pytest.fixture
def client(engine):
    """TestClient wired to the test DB — no mocks on extraction or API key."""
    app.dependency_overrides[triage_module._engine] = lambda: engine
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# Phrases deliberately avoid every keyword in extract.py's _extract_risk_signals
# and rules.py's _RED_FLAG_KEYWORDS so deterministic detection would score 0.0.
# The LLM must recognise the clinical intent and assign conviction >= threshold.
#
# (id, prompt, expected_flag)
SCENARIOS = [
    (
        "suicidal_conviction",
        "I don't see the point in living anymore, I've been thinking about not waking up",
        "SUICIDAL_IDEATION",
    ),
    (
        "self_harm_conviction",
        "I've been using a razor on my arms when things get overwhelming",
        "SELF_HARM",
    ),
    (
        "homicidal_conviction",
        "I keep having violent thoughts about doing something terrible to my neighbor, I'm scared I might act on them",
        "HOMICIDAL_IDEATION",
    ),
    (
        "cannot_breathe_conviction",
        "I feel like I'm suffocating, my lungs won't fill up with air no matter how hard I try",
        "CANNOT_BREATHE",
    ),
    (
        "chest_pain_conviction",
        "There's a crushing pressure behind my sternum and my left arm is tingling",
        "CHEST_PAIN",
    ),
    (
        "neuro_deficit_conviction",
        "My words are coming out jumbled and one side of my face feels like it's melting, I can't grip things with my right hand",
        "NEURO_DEFICIT",
    ),
    (
        "bleeding_conviction",
        "I gashed my leg deeply and the blood keeps pouring out everywhere, it won't clot at all",
        "BLEEDING_UNCONTROLLED",
    ),
]


@pytest.mark.parametrize(
    "name,prompt,expected_flag",
    SCENARIOS,
    ids=[s[0] for s in SCENARIOS],
)
def test_conviction_escalation(client, name, prompt, expected_flag):
    """Verify the LLM assigns conviction scores that trigger escalation."""
    # Create incident
    inc = client.post("/api/triage/incidents", json={"domain": "medical"})
    assert inc.status_code == 200
    inc_id = inc.json()["id"]

    # Send message through real LLM extraction pipeline
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

    # Acuity must be at most 2
    assert result["acuity"] <= 2, (
        f"[{name}] expected acuity <= 2, got {result['acuity']}"
    )

    # Verify the expected flag was triggered
    triggered = result["triggered_risk_flags"]
    flag_types = [f["flag_type"] for f in triggered]
    assert expected_flag in flag_types, (
        f"[{name}] expected {expected_flag} in triggered_risk_flags, "
        f"got {flag_types}"
    )
    matched = next(f for f in triggered if f["flag_type"] == expected_flag)

    # LLM must have assigned a positive conviction that exceeded the threshold
    assert matched["conviction"] > 0, (
        f"[{name}] expected conviction > 0, got {matched['conviction']}"
    )
    assert matched["conviction"] >= matched["threshold"], (
        f"[{name}] conviction {matched['conviction']} should be >= "
        f"threshold {matched['threshold']}"
    )

    # Incident status must be ESCALATED
    inc_check = client.get(f"/api/triage/incidents/{inc_id}")
    assert inc_check.json()["status"] == IncidentStatus.ESCALATED.value, (
        f"[{name}] expected status ESCALATED, got {inc_check.json()['status']}"
    )
