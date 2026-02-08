"""Deterministic medical triage rules — ESI-like acuity + red-flag detection.

How it works:
  1. Patient says something (text or voice)
  2. The LLM extracts structured data (symptoms, pain, vitals, mental status)
  3. THIS FILE runs deterministic rules on that data — no AI involved here
  4. Rules detect "red flags" (dangerous conditions) and compute an urgency score

The LLM is an untrusted helper. Final triage decisions (acuity, escalation)
are always made by these deterministic rules, never by the model.

Acuity levels (ESI-like, 1 = most urgent):
  1 — Immediate life threat (unresponsive, heart attack + can't breathe)
  2 — High risk (confused, severe pain 8+, multiple red flags)
  3 — Moderate (single red flag, moderate pain, abnormal vitals)
  4 — Mild (some symptoms but nothing alarming)
  5 — Minor (simple complaint, no concerning findings)

Escalation: acuity 1 or 2 → escalate to a human professional immediately.
"""

from __future__ import annotations

from services.api.src.api.domains.medical.schemas import (
    MedicalAssessment,
    MedicalExtraction,
    RedFlag,
)

# ---------------------------------------------------------------------------
# Red-flag rules — keywords that trigger immediate concern
#
# These are matched against the patient's chief_complaint + symptoms.
# If ANY of these appear, the case gets flagged.
# ---------------------------------------------------------------------------

_RED_FLAG_KEYWORDS = {
    # Cardiac
    "chest pain": "Possible cardiac event",
    "heart attack": "Possible cardiac event",
    "cardiac arrest": "Possible cardiac event",

    # Respiratory
    "difficulty breathing": "Respiratory distress",
    "shortness of breath": "Respiratory distress",
    "can't breathe": "Respiratory distress",
    "cannot breathe": "Respiratory distress",
    "choking": "Respiratory distress",

    # Bleeding
    "severe bleeding": "Hemorrhage risk",
    "uncontrolled bleeding": "Hemorrhage risk",
    "bleeding heavily": "Hemorrhage risk",

    # Neurological
    "seizure": "Neurological emergency",
    "convulsion": "Neurological emergency",
    "stroke": "Possible CVA",
    "slurred speech": "Possible CVA",
    "facial drooping": "Possible CVA",

    # Consciousness
    "loss of consciousness": "Altered consciousness",
    "passed out": "Altered consciousness",
    "fainted": "Altered consciousness",

    # Patient expressing imminent danger
    "dying": "Patient reports imminent death",
    "going to die": "Patient reports imminent death",

    # Psychiatric
    "suicidal": "Psychiatric emergency",
    "self-harm": "Psychiatric emergency",
    "kill myself": "Psychiatric emergency",

    # Allergic / toxic
    "anaphylaxis": "Severe allergic reaction",
    "severe allergic reaction": "Severe allergic reaction",
    "overdose": "Possible overdose",
}


def detect_red_flags(extraction: MedicalExtraction) -> list[RedFlag]:
    """Scan extraction for red-flag conditions.

    Checks three sources:
    - chief_complaint (what the patient said first)
    - symptoms list (structured by the LLM)
    - mental_status field
    - vital signs (heart rate, blood pressure, O2, temperature)
    """
    flags: list[RedFlag] = []

    # Build one searchable string from complaint + all symptoms
    text_fields = [extraction.chief_complaint.lower()] + [
        s.lower() for s in extraction.symptoms
    ]
    searchable = " ".join(text_fields)

    # Keyword scan
    for keyword, reason in _RED_FLAG_KEYWORDS.items():
        if keyword in searchable:
            flags.append(RedFlag(name=keyword, reason=reason))

    # Dangerous combination: chest pain + breathing problems
    has_chest_pain = "chest pain" in searchable
    has_sob = "shortness of breath" in searchable or "difficulty breathing" in searchable
    if has_chest_pain and has_sob:
        flags.append(RedFlag(
            name="chest_pain_with_sob",
            reason="Chest pain combined with respiratory distress — high-risk cardiac",
        ))

    # Altered mental status (confused or unresponsive)
    if extraction.mental_status in ("confused", "unresponsive"):
        flags.append(RedFlag(
            name="altered_mental_status",
            reason=f"Mental status: {extraction.mental_status}",
        ))

    # Vital-sign red flags — numbers outside safe ranges
    vitals = extraction.vitals
    if vitals.heart_rate is not None and vitals.heart_rate > 150:
        flags.append(RedFlag(name="tachycardia", reason=f"HR {vitals.heart_rate} > 150"))
    if vitals.heart_rate is not None and vitals.heart_rate < 40:
        flags.append(RedFlag(name="bradycardia", reason=f"HR {vitals.heart_rate} < 40"))
    if vitals.oxygen_saturation is not None and vitals.oxygen_saturation < 90:
        flags.append(RedFlag(
            name="hypoxia", reason=f"SpO2 {vitals.oxygen_saturation}% < 90%",
        ))
    if vitals.temperature_f is not None and vitals.temperature_f >= 104.0:
        flags.append(RedFlag(
            name="high_fever", reason=f"Temp {vitals.temperature_f}°F >= 104°F",
        ))
    if vitals.blood_pressure_systolic is not None and vitals.blood_pressure_systolic < 80:
        flags.append(RedFlag(
            name="hypotension", reason=f"SBP {vitals.blood_pressure_systolic} < 80",
        ))

    return flags


# ---------------------------------------------------------------------------
# ESI acuity scoring — maps red flags + extraction data to urgency 1-5
# ---------------------------------------------------------------------------

def compute_acuity(extraction: MedicalExtraction, red_flags: list[RedFlag]) -> int:
    """Compute ESI-like acuity level 1 (most urgent) to 5 (least urgent).

    Level 1: Immediate life threat (unresponsive, cardiac arrest indicators)
    Level 2: High-risk / confused / severe pain / multiple red flags
    Level 3: Moderate — abnormal vitals or moderate pain
    Level 4: Mild symptoms, low complexity
    Level 5: Minor complaint, no concerning findings
    """
    # ESI-1: unresponsive or life-threatening combination
    if extraction.mental_status == "unresponsive":
        return 1
    life_threat_flags = {"chest_pain_with_sob", "severe bleeding", "anaphylaxis",
                         "heart attack", "cardiac arrest", "dying", "going to die",
                         "overdose"}
    if any(f.name in life_threat_flags for f in red_flags):
        return 1

    # ESI-2: confused, or >=2 red flags, or severe pain (8-10)
    if extraction.mental_status == "confused":
        return 2
    if len(red_flags) >= 2:
        return 2
    if extraction.pain_scale is not None and extraction.pain_scale >= 8:
        return 2

    # ESI-3: any red flag, moderate pain (5-7), abnormal vitals
    if len(red_flags) >= 1:
        return 3
    if extraction.pain_scale is not None and extraction.pain_scale >= 5:
        return 3
    vitals = extraction.vitals
    if vitals.heart_rate is not None and (vitals.heart_rate > 100 or vitals.heart_rate < 50):
        return 3
    if vitals.temperature_f is not None and vitals.temperature_f >= 101.0:
        return 3
    if vitals.oxygen_saturation is not None and vitals.oxygen_saturation < 95:
        return 3

    # ESI-4: some symptoms or history but nothing alarming
    if len(extraction.symptoms) >= 2 or extraction.pain_scale is not None:
        return 4

    # ESI-5: minor
    return 5


# ---------------------------------------------------------------------------
# Full assessment — ties everything together
# ---------------------------------------------------------------------------

def assess(extraction: MedicalExtraction) -> MedicalAssessment:
    """Run deterministic triage on an extraction, return assessment.

    This is the final decision maker. The LLM extracted the data,
    but this function decides: how urgent? escalate? discharge?
    """
    red_flags = detect_red_flags(extraction)
    acuity = compute_acuity(extraction, red_flags)

    # Acuity 1-2 = escalate immediately to a human
    escalate = acuity <= 2
    if escalate:
        disposition = "escalate"
    elif acuity >= 4 and not red_flags:
        disposition = "discharge"
    else:
        disposition = "continue"

    flag_names = [f.name for f in red_flags]
    summary_parts = [f"ESI-{acuity}"]
    if red_flags:
        summary_parts.append(f"red flags: {', '.join(flag_names)}")
    if escalate:
        summary_parts.append("ESCALATE")

    return MedicalAssessment(
        acuity=acuity,
        escalate=escalate,
        red_flags=red_flags,
        disposition=disposition,
        summary=" | ".join(summary_parts),
    )
