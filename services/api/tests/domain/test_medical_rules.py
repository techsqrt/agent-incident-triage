"""Tests for medical triage deterministic rules."""

from services.api.src.api.domains.medical.rules import (
    assess,
    compute_acuity,
    detect_red_flags,
)
from services.api.src.api.domains.medical.schemas import (
    MedicalExtraction,
    VitalSigns,
)


# ---------------------------------------------------------------------------
# Red-flag detection
# ---------------------------------------------------------------------------

class TestRedFlagDetection:
    def test_no_red_flags_for_minor_complaint(self):
        e = MedicalExtraction(chief_complaint="runny nose", symptoms=["congestion"])
        flags = detect_red_flags(e)
        assert len(flags) == 0

    def test_chest_pain_flag(self):
        e = MedicalExtraction(chief_complaint="chest pain")
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "chest pain" in names

    def test_sob_flag(self):
        e = MedicalExtraction(symptoms=["shortness of breath"])
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "shortness of breath" in names

    def test_chest_pain_with_sob_combination(self):
        e = MedicalExtraction(
            chief_complaint="chest pain",
            symptoms=["shortness of breath"],
        )
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "chest_pain_with_sob" in names

    def test_altered_mental_status_confused(self):
        e = MedicalExtraction(mental_status="confused")
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "altered_mental_status" in names

    def test_altered_mental_status_unresponsive(self):
        e = MedicalExtraction(mental_status="unresponsive")
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "altered_mental_status" in names

    def test_alert_mental_status_no_flag(self):
        e = MedicalExtraction(mental_status="alert")
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "altered_mental_status" not in names

    def test_tachycardia_flag(self):
        e = MedicalExtraction(vitals=VitalSigns(heart_rate=160))
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "tachycardia" in names

    def test_bradycardia_flag(self):
        e = MedicalExtraction(vitals=VitalSigns(heart_rate=35))
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "bradycardia" in names

    def test_hypoxia_flag(self):
        e = MedicalExtraction(vitals=VitalSigns(oxygen_saturation=85))
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "hypoxia" in names

    def test_high_fever_flag(self):
        e = MedicalExtraction(vitals=VitalSigns(temperature_f=105.0))
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "high_fever" in names

    def test_hypotension_flag(self):
        e = MedicalExtraction(vitals=VitalSigns(blood_pressure_systolic=70))
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "hypotension" in names

    def test_seizure_keyword(self):
        e = MedicalExtraction(symptoms=["seizure"])
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "seizure" in names

    def test_suicidal_flag(self):
        e = MedicalExtraction(chief_complaint="suicidal thoughts")
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "suicidal" in names


# ---------------------------------------------------------------------------
# ESI acuity scoring
# ---------------------------------------------------------------------------

class TestAcuityScoring:
    def test_esi_1_unresponsive(self):
        e = MedicalExtraction(mental_status="unresponsive")
        flags = detect_red_flags(e)
        assert compute_acuity(e, flags) == 1

    def test_esi_1_chest_pain_with_sob(self):
        e = MedicalExtraction(
            chief_complaint="chest pain",
            symptoms=["shortness of breath"],
        )
        flags = detect_red_flags(e)
        assert compute_acuity(e, flags) == 1

    def test_esi_1_anaphylaxis(self):
        e = MedicalExtraction(symptoms=["anaphylaxis"])
        flags = detect_red_flags(e)
        assert compute_acuity(e, flags) == 1

    def test_esi_2_confused(self):
        e = MedicalExtraction(mental_status="confused")
        flags = detect_red_flags(e)
        assert compute_acuity(e, flags) == 2

    def test_esi_2_severe_pain(self):
        e = MedicalExtraction(pain_scale=9)
        flags = detect_red_flags(e)
        assert compute_acuity(e, flags) == 2

    def test_esi_2_multiple_red_flags(self):
        e = MedicalExtraction(
            vitals=VitalSigns(heart_rate=160, oxygen_saturation=85),
        )
        flags = detect_red_flags(e)
        assert len(flags) >= 2
        assert compute_acuity(e, flags) == 2

    def test_esi_3_single_red_flag(self):
        e = MedicalExtraction(vitals=VitalSigns(temperature_f=105.0))
        flags = detect_red_flags(e)
        assert len(flags) == 1
        assert compute_acuity(e, flags) == 3

    def test_esi_3_moderate_pain(self):
        e = MedicalExtraction(pain_scale=6)
        flags = detect_red_flags(e)
        assert compute_acuity(e, flags) == 3

    def test_esi_3_elevated_hr(self):
        e = MedicalExtraction(vitals=VitalSigns(heart_rate=110))
        flags = detect_red_flags(e)
        assert compute_acuity(e, flags) == 3

    def test_esi_3_fever(self):
        e = MedicalExtraction(vitals=VitalSigns(temperature_f=102.0))
        flags = detect_red_flags(e)
        assert compute_acuity(e, flags) == 3

    def test_esi_4_multiple_symptoms(self):
        e = MedicalExtraction(symptoms=["cough", "runny nose"])
        flags = detect_red_flags(e)
        assert compute_acuity(e, flags) == 4

    def test_esi_4_mild_pain(self):
        e = MedicalExtraction(pain_scale=3)
        flags = detect_red_flags(e)
        assert compute_acuity(e, flags) == 4

    def test_esi_5_minor_complaint(self):
        e = MedicalExtraction(chief_complaint="paper cut")
        flags = detect_red_flags(e)
        assert compute_acuity(e, flags) == 5


# ---------------------------------------------------------------------------
# Full assessment
# ---------------------------------------------------------------------------

class TestAssess:
    def test_critical_patient_escalates(self):
        e = MedicalExtraction(
            chief_complaint="chest pain",
            symptoms=["shortness of breath"],
            pain_scale=9,
            mental_status="alert",
        )
        result = assess(e)
        assert result.acuity == 1
        assert result.escalate is True
        assert result.disposition == "escalate"
        assert len(result.red_flags) > 0

    def test_minor_patient_no_escalation(self):
        e = MedicalExtraction(
            chief_complaint="runny nose",
            symptoms=["congestion"],
        )
        result = assess(e)
        assert result.acuity >= 4
        assert result.escalate is False
        assert result.disposition == "discharge"

    def test_moderate_patient_continues(self):
        e = MedicalExtraction(
            chief_complaint="headache",
            pain_scale=6,
        )
        result = assess(e)
        assert result.acuity == 3
        assert result.escalate is False
        assert result.disposition == "continue"

    def test_summary_includes_esi(self):
        e = MedicalExtraction(chief_complaint="cough")
        result = assess(e)
        assert "ESI-" in result.summary

    def test_summary_includes_escalate_when_critical(self):
        e = MedicalExtraction(mental_status="unresponsive")
        result = assess(e)
        assert "ESCALATE" in result.summary
