"""E2E conviction-based escalation tests via mocked extraction + rules.

Each test sends a synonymous patient message (avoiding exact flagged keywords)
through the full pipeline with extract_from_text mocked to return conviction
scores above threshold but below 1.0 — simulating what an LLM would produce.

This validates that the conviction-threshold escalation path works correctly:
  API endpoint -> mocked extraction (conviction scores) -> deterministic rules -> escalation

The direct boolean/tri-state signal stays False/unknown; only the conviction
score exceeds the threshold, proving the second branch of evaluate_risk_signals
triggers escalation independently of keyword detection.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from services.api.src.api.domains.medical.schemas import (
    MedicalExtraction,
    RiskSignals,
)
from services.api.src.api.main import app
from services.api.src.api.routes import triage as triage_module
from services.api.src.api.schemas.enums import IncidentStatus

pytestmark = pytest.mark.e2e


@pytest.fixture
def client(engine):
    """TestClient with overridden DB engine and LLM extraction disabled."""
    app.dependency_overrides[triage_module._engine] = lambda: engine
    with patch(
        "services.api.src.api.routes.triage.settings.openai_api_key", ""
    ):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


def _make_extraction(prompt: str, conviction_field: str, conviction_value: float):
    """Build a MedicalExtraction with only the specified conviction set.

    All boolean/tri-state signal values stay at their defaults (False/unknown)
    so the ONLY escalation path is conviction >= threshold.
    """
    return MedicalExtraction(
        chief_complaint=prompt,
        risk_signals=RiskSignals(**{conviction_field: conviction_value}),
    )


# Phrases deliberately avoid every keyword in extract.py's _extract_risk_signals
# and rules.py's _RED_FLAG_KEYWORDS so deterministic detection returns 0.0.
#
# (id, prompt, expected_flag, conviction_field, conviction_value)
#
# Conviction values sit safely above each threshold but well below 1.0:
#   psychiatric (threshold 0.2) → 0.6
#   homicidal   (threshold 0.4) → 0.7
#   physical    (threshold 0.5) → 0.75
SCENARIOS = [
    (
        "suicidal_conviction",
        "I don't see the point in living anymore, I've been thinking about not waking up",
        "SUICIDAL_IDEATION",
        "suicidal_ideation_conviction",
        0.6,
    ),
    (
        "self_harm_conviction",
        "I've been using a razor on my arms when things get overwhelming",
        "SELF_HARM",
        "self_harm_intent_conviction",
        0.6,
    ),
    (
        "homicidal_conviction",
        "I keep having violent thoughts about doing something terrible to my neighbor",
        "HOMICIDAL_IDEATION",
        "homicidal_ideation_conviction",
        0.7,
    ),
    (
        "cannot_breathe_conviction",
        "I feel like I'm suffocating, my lungs won't fill up with air",
        "CANNOT_BREATHE",
        "can_breathe_conviction",
        0.75,
    ),
    (
        "chest_pain_conviction",
        "There's a crushing pressure behind my sternum and my left arm is tingling",
        "CHEST_PAIN",
        "chest_pain_conviction",
        0.75,
    ),
    (
        "neuro_deficit_conviction",
        "My words are coming out jumbled and one side of my face feels like it's melting",
        "NEURO_DEFICIT",
        "neuro_deficit_conviction",
        0.75,
    ),
    (
        "bleeding_conviction",
        "I gashed my leg and the blood keeps pouring out, it won't clot at all",
        "BLEEDING_UNCONTROLLED",
        "bleeding_uncontrolled_conviction",
        0.75,
    ),
]


@pytest.mark.parametrize(
    "name,prompt,expected_flag,conviction_field,conviction_value",
    SCENARIOS,
    ids=[s[0] for s in SCENARIOS],
)
def test_conviction_escalation(
    client, name, prompt, expected_flag, conviction_field, conviction_value
):
    """Verify conviction-based escalation triggers for synonymous phrases."""
    # Create incident
    inc = client.post("/api/triage/incidents", json={"domain": "medical"})
    assert inc.status_code == 200
    inc_id = inc.json()["id"]

    # Mock extract_from_text to return conviction score without direct keyword match
    extraction = _make_extraction(prompt, conviction_field, conviction_value)
    with patch(
        "services.api.src.api.routes.triage.extract_from_text",
        return_value=extraction,
    ):
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

    # Acuity must be at most 2 (risk signal escalation bumps to 2)
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

    # Key assertion: signal_value must be False/unknown (NOT a direct detection).
    # This proves escalation came from conviction >= threshold, not keyword match.
    assert matched["signal_value"] in ("False", "unknown"), (
        f"[{name}] expected conviction-based detection (False/unknown), "
        f"got signal_value={matched['signal_value']}"
    )

    # Conviction must equal what we injected and exceed its threshold
    assert matched["conviction"] == conviction_value, (
        f"[{name}] conviction mismatch: expected {conviction_value}, "
        f"got {matched['conviction']}"
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
