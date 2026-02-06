"""Deterministic keyword-based medical extraction.

Used as fallback when OPENAI_API_KEY is not set, and as the default
extraction path for the text chat endpoint.
"""

from services.api.src.api.domains.medical.schemas import MedicalExtraction

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

    return MedicalExtraction(
        chief_complaint=text[:200],
        symptoms=symptoms,
        pain_scale=pain_scale,
        mental_status=mental_status,
    )
