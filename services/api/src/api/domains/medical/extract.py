"""Deterministic keyword-based medical extraction.

Used as fallback when OPENAI_API_KEY is not set, and as the default
extraction path for the text chat endpoint.
"""

from services.api.src.api.domains.medical.schemas import (
    CriticalRedFlagType,
    MedicalExtraction,
    RiskSignals,
)

# Symptoms detected by keyword matching
_SYMPTOM_KEYWORDS = [
    "chest pain", "shortness of breath", "difficulty breathing",
    "headache", "nausea", "vomiting", "dizziness", "fever",
    "cough", "sore throat", "abdominal pain", "back pain",
    "seizure", "bleeding", "rash", "fatigue",
]


def extract_from_text(text: str) -> MedicalExtraction:
    """Extract medical data from free text using keyword matching."""
    symptoms = []
    pain_scale = None
    mental_status = "alert"

    lower = text.lower()

    for kw in _SYMPTOM_KEYWORDS:
        if kw in lower:
            symptoms.append(kw)

    # Pain scale detection
    for i in range(11):
        if f"pain {i}" in lower or f"pain is {i}" in lower or f"pain level {i}" in lower:
            pain_scale = i
            break
        if f"{i}/10" in lower or f"{i} out of 10" in lower:
            pain_scale = i
            break

    # Mental status detection
    if "confused" in lower or "confusion" in lower:
        mental_status = "confused"
    elif "unresponsive" in lower:
        mental_status = "unresponsive"

    # Risk signals extraction (keyword-based with high conviction when detected)
    risk_signals = _extract_risk_signals(lower)

    return MedicalExtraction(
        chief_complaint=text[:200],
        symptoms=symptoms,
        pain_scale=pain_scale,
        mental_status=mental_status,
        risk_signals=risk_signals,
    )


def _extract_risk_signals(text: str) -> RiskSignals:
    """Extract risk signals from text using keyword matching.

    When a keyword is detected, we set high conviction (0.9).
    When not detected, conviction is 0.0 (unknown).
    """
    red_flags_detected = []
    missing_fields = []

    # Suicidal ideation keywords
    suicidal_keywords = ["suicidal", "kill myself", "end my life", "want to die",
                         "finish with myself", "end it all", "take my life"]
    suicidal_ideation = any(kw in text for kw in suicidal_keywords)
    suicidal_conviction = 0.9 if suicidal_ideation else 0.0
    if suicidal_ideation:
        red_flags_detected.append(CriticalRedFlagType.SUICIDAL_IDEATION)

    # Self-harm keywords
    self_harm_keywords = ["self-harm", "self harm", "hurt myself", "cut myself",
                          "harm myself", "injure myself"]
    self_harm_intent = any(kw in text for kw in self_harm_keywords)
    self_harm_conviction = 0.9 if self_harm_intent else 0.0
    if self_harm_intent:
        red_flags_detected.append(CriticalRedFlagType.SELF_HARM)

    # Homicidal ideation keywords
    homicidal_keywords = ["kill someone", "hurt someone", "harm others", "homicidal"]
    homicidal_ideation = any(kw in text for kw in homicidal_keywords)
    homicidal_conviction = 0.9 if homicidal_ideation else 0.0
    if homicidal_ideation:
        red_flags_detected.append(CriticalRedFlagType.HOMICIDAL_IDEATION)

    # Breathing issues
    cant_breathe_keywords = ["can't breathe", "cannot breathe", "cant breathe",
                             "struggling to breathe", "hard to breathe", "difficulty breathing"]
    cant_breathe = any(kw in text for kw in cant_breathe_keywords)
    can_breathe = "no" if cant_breathe else "unknown"
    can_breathe_conviction = 0.9 if cant_breathe else 0.0
    if cant_breathe:
        red_flags_detected.append(CriticalRedFlagType.CANNOT_BREATHE)

    # Chest pain
    chest_pain_keywords = ["chest pain", "pain in my chest", "chest hurts", "heart pain"]
    has_chest_pain = any(kw in text for kw in chest_pain_keywords)
    chest_pain = "yes" if has_chest_pain else "unknown"
    chest_pain_conviction = 0.9 if has_chest_pain else 0.0
    if has_chest_pain:
        red_flags_detected.append(CriticalRedFlagType.CHEST_PAIN)

    # Neurological deficit
    neuro_keywords = ["stroke", "seizure", "slurred speech", "facial drooping",
                      "can't move", "numbness", "paralysis", "weakness on one side"]
    has_neuro = any(kw in text for kw in neuro_keywords)
    neuro_deficit = "yes" if has_neuro else "unknown"
    neuro_conviction = 0.9 if has_neuro else 0.0
    if has_neuro:
        red_flags_detected.append(CriticalRedFlagType.NEURO_DEFICIT)

    # Uncontrolled bleeding
    bleeding_keywords = ["uncontrolled bleeding", "severe bleeding", "bleeding heavily",
                         "won't stop bleeding", "blood everywhere"]
    has_bleeding = any(kw in text for kw in bleeding_keywords)
    bleeding_uncontrolled = "yes" if has_bleeding else "unknown"
    bleeding_conviction = 0.9 if has_bleeding else 0.0
    if has_bleeding:
        red_flags_detected.append(CriticalRedFlagType.BLEEDING_UNCONTROLLED)

    # Check for missing fields
    if "age" not in text and "years old" not in text and "year old" not in text:
        missing_fields.append("age")

    return RiskSignals(
        suicidal_ideation=suicidal_ideation,
        suicidal_ideation_conviction=suicidal_conviction,
        self_harm_intent=self_harm_intent,
        self_harm_intent_conviction=self_harm_conviction,
        homicidal_ideation=homicidal_ideation,
        homicidal_ideation_conviction=homicidal_conviction,
        can_breathe=can_breathe,
        can_breathe_conviction=can_breathe_conviction,
        chest_pain=chest_pain,
        chest_pain_conviction=chest_pain_conviction,
        neuro_deficit=neuro_deficit,
        neuro_deficit_conviction=neuro_conviction,
        bleeding_uncontrolled=bleeding_uncontrolled,
        bleeding_uncontrolled_conviction=bleeding_conviction,
        red_flags_detected=red_flags_detected,
        missing_fields=missing_fields,
    )
