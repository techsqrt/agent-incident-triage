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
    CriticalRedFlagType,
    MedicalAssessment,
    MedicalExtraction,
    RedFlag,
    RiskSignals,
    TriggeredRiskFlag,
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

# ---------------------------------------------------------------------------
# Risk signal conviction thresholds for deterministic escalation
#
# These thresholds are CONSERVATIVE — low thresholds for high-risk signals
# mean we escalate even with moderate confidence. Safety first.
# ---------------------------------------------------------------------------

RISK_SIGNAL_THRESHOLDS = {
    # Psychiatric signals — very low threshold (escalate even with slight suspicion)
    CriticalRedFlagType.SUICIDAL_IDEATION: 0.2,
    CriticalRedFlagType.SELF_HARM: 0.2,
    CriticalRedFlagType.HOMICIDAL_IDEATION: 0.4,

    # Physical signals — moderate threshold
    CriticalRedFlagType.CANNOT_BREATHE: 0.5,
    CriticalRedFlagType.CHEST_PAIN: 0.5,
    CriticalRedFlagType.NEURO_DEFICIT: 0.5,
    CriticalRedFlagType.BLEEDING_UNCONTROLLED: 0.5,
}

# Human-readable explanations for each triggered flag
_RISK_FLAG_EXPLANATIONS = {
    CriticalRedFlagType.SUICIDAL_IDEATION: "Patient may be expressing suicidal thoughts; policy requires immediate escalation.",
    CriticalRedFlagType.SELF_HARM: "Patient may be expressing intent to self-harm; policy requires immediate escalation.",
    CriticalRedFlagType.HOMICIDAL_IDEATION: "Patient may be expressing intent to harm others; policy requires immediate escalation.",
    CriticalRedFlagType.CANNOT_BREATHE: "Patient reports difficulty breathing; this is a potential emergency.",
    CriticalRedFlagType.CHEST_PAIN: "Patient reports chest pain; cardiac emergency must be ruled out.",
    CriticalRedFlagType.NEURO_DEFICIT: "Patient shows signs of neurological deficit; possible stroke or emergency.",
    CriticalRedFlagType.BLEEDING_UNCONTROLLED: "Patient reports uncontrolled bleeding; hemorrhage risk.",
}


def evaluate_risk_signals(risk_signals: RiskSignals) -> list[TriggeredRiskFlag]:
    """Evaluate risk signals against thresholds and return triggered flags.

    This is the second layer of deterministic escalation.
    A flag is triggered if:
    - The signal value indicates danger (true for bool, "yes"/"no" for tri-state) OR
    - The conviction score exceeds the threshold for that flag type

    Returns list of triggered flags with human-readable explanations.
    """
    triggered: list[TriggeredRiskFlag] = []

    # Suicidal ideation: escalate if true OR conviction >= threshold
    threshold = RISK_SIGNAL_THRESHOLDS[CriticalRedFlagType.SUICIDAL_IDEATION]
    if risk_signals.suicidal_ideation or risk_signals.suicidal_ideation_conviction >= threshold:
        triggered.append(TriggeredRiskFlag(
            flag_type=CriticalRedFlagType.SUICIDAL_IDEATION,
            signal_value=str(risk_signals.suicidal_ideation),
            conviction=risk_signals.suicidal_ideation_conviction,
            threshold=threshold,
            human_explanation=_RISK_FLAG_EXPLANATIONS[CriticalRedFlagType.SUICIDAL_IDEATION],
        ))

    # Self-harm intent: escalate if true OR conviction >= threshold
    threshold = RISK_SIGNAL_THRESHOLDS[CriticalRedFlagType.SELF_HARM]
    if risk_signals.self_harm_intent or risk_signals.self_harm_intent_conviction >= threshold:
        triggered.append(TriggeredRiskFlag(
            flag_type=CriticalRedFlagType.SELF_HARM,
            signal_value=str(risk_signals.self_harm_intent),
            conviction=risk_signals.self_harm_intent_conviction,
            threshold=threshold,
            human_explanation=_RISK_FLAG_EXPLANATIONS[CriticalRedFlagType.SELF_HARM],
        ))

    # Homicidal ideation: escalate if true OR conviction >= threshold
    threshold = RISK_SIGNAL_THRESHOLDS[CriticalRedFlagType.HOMICIDAL_IDEATION]
    if risk_signals.homicidal_ideation or risk_signals.homicidal_ideation_conviction >= threshold:
        triggered.append(TriggeredRiskFlag(
            flag_type=CriticalRedFlagType.HOMICIDAL_IDEATION,
            signal_value=str(risk_signals.homicidal_ideation),
            conviction=risk_signals.homicidal_ideation_conviction,
            threshold=threshold,
            human_explanation=_RISK_FLAG_EXPLANATIONS[CriticalRedFlagType.HOMICIDAL_IDEATION],
        ))

    # Can't breathe: escalate if "no" OR conviction >= threshold
    threshold = RISK_SIGNAL_THRESHOLDS[CriticalRedFlagType.CANNOT_BREATHE]
    if risk_signals.can_breathe == "no" or risk_signals.can_breathe_conviction >= threshold:
        triggered.append(TriggeredRiskFlag(
            flag_type=CriticalRedFlagType.CANNOT_BREATHE,
            signal_value=risk_signals.can_breathe,
            conviction=risk_signals.can_breathe_conviction,
            threshold=threshold,
            human_explanation=_RISK_FLAG_EXPLANATIONS[CriticalRedFlagType.CANNOT_BREATHE],
        ))

    # Chest pain: escalate if "yes" OR conviction >= threshold
    threshold = RISK_SIGNAL_THRESHOLDS[CriticalRedFlagType.CHEST_PAIN]
    if risk_signals.chest_pain == "yes" or risk_signals.chest_pain_conviction >= threshold:
        triggered.append(TriggeredRiskFlag(
            flag_type=CriticalRedFlagType.CHEST_PAIN,
            signal_value=risk_signals.chest_pain,
            conviction=risk_signals.chest_pain_conviction,
            threshold=threshold,
            human_explanation=_RISK_FLAG_EXPLANATIONS[CriticalRedFlagType.CHEST_PAIN],
        ))

    # Neuro deficit: escalate if "yes" OR conviction >= threshold
    threshold = RISK_SIGNAL_THRESHOLDS[CriticalRedFlagType.NEURO_DEFICIT]
    if risk_signals.neuro_deficit == "yes" or risk_signals.neuro_deficit_conviction >= threshold:
        triggered.append(TriggeredRiskFlag(
            flag_type=CriticalRedFlagType.NEURO_DEFICIT,
            signal_value=risk_signals.neuro_deficit,
            conviction=risk_signals.neuro_deficit_conviction,
            threshold=threshold,
            human_explanation=_RISK_FLAG_EXPLANATIONS[CriticalRedFlagType.NEURO_DEFICIT],
        ))

    # Uncontrolled bleeding: escalate if "yes" OR conviction >= threshold
    threshold = RISK_SIGNAL_THRESHOLDS[CriticalRedFlagType.BLEEDING_UNCONTROLLED]
    if risk_signals.bleeding_uncontrolled == "yes" or risk_signals.bleeding_uncontrolled_conviction >= threshold:
        triggered.append(TriggeredRiskFlag(
            flag_type=CriticalRedFlagType.BLEEDING_UNCONTROLLED,
            signal_value=risk_signals.bleeding_uncontrolled,
            conviction=risk_signals.bleeding_uncontrolled_conviction,
            threshold=threshold,
            human_explanation=_RISK_FLAG_EXPLANATIONS[CriticalRedFlagType.BLEEDING_UNCONTROLLED],
        ))

    return triggered


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

    Two-layer escalation:
    1. Keyword-based red flags (existing system)
    2. Risk signal conviction thresholds (new system)

    If EITHER layer triggers escalation, we escalate.
    """
    # Layer 1: Keyword-based red flag detection
    red_flags = detect_red_flags(extraction)

    # Layer 2: Risk signal conviction threshold evaluation
    triggered_risk_flags = evaluate_risk_signals(extraction.risk_signals)

    # Add any triggered risk flags to the keyword red flags list
    # to ensure they're counted in acuity calculation
    for trf in triggered_risk_flags:
        red_flags.append(RedFlag(
            name=trf.flag_type.value,
            reason=trf.human_explanation,
            severity="critical",
        ))

    # Compute acuity based on ALL detected red flags
    acuity = compute_acuity(extraction, red_flags)

    # Escalation: acuity 1-2 OR any critical risk signal triggered
    escalate_by_acuity = acuity <= 2
    escalate_by_risk = len(triggered_risk_flags) > 0
    escalate = escalate_by_acuity or escalate_by_risk

    # If risk signals triggered escalation, bump acuity to at least 2
    if escalate_by_risk and acuity > 2:
        acuity = 2

    # Determine disposition
    if escalate:
        disposition = "escalate"
    elif acuity >= 4 and not red_flags:
        disposition = "discharge"
    else:
        disposition = "continue"

    # Build summary
    flag_names = [f.name for f in red_flags]
    summary_parts = [f"ESI-{acuity}"]
    if red_flags:
        summary_parts.append(f"red flags: {', '.join(flag_names)}")
    if escalate:
        summary_parts.append("ESCALATE")

    # Build escalation reason from triggered risk flags
    escalation_reason = ""
    if triggered_risk_flags:
        reasons = [trf.human_explanation for trf in triggered_risk_flags]
        escalation_reason = " ".join(reasons)

    return MedicalAssessment(
        acuity=acuity,
        escalate=escalate,
        red_flags=red_flags,
        triggered_risk_flags=triggered_risk_flags,
        escalation_reason=escalation_reason,
        disposition=disposition,
        summary=" | ".join(summary_parts),
    )
