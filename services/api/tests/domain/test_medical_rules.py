"""Tests for medical triage deterministic rules."""

from services.api.src.api.domains.medical.rules import (
    assess,
    compute_acuity,
    detect_red_flags,
    evaluate_risk_signals,
    RISK_SIGNAL_THRESHOLDS,
)
from services.api.src.api.domains.medical.schemas import (
    CriticalRedFlagType,
    MedicalExtraction,
    RiskSignals,
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

    def test_heart_attack_flag(self):
        e = MedicalExtraction(chief_complaint="I think I'm having a heart attack")
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "heart attack" in names

    def test_dying_flag(self):
        e = MedicalExtraction(chief_complaint="I feel like I'm dying")
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "dying" in names

    def test_cant_breathe_flag(self):
        e = MedicalExtraction(symptoms=["can't breathe"])
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "can't breathe" in names

    def test_overdose_flag(self):
        e = MedicalExtraction(chief_complaint="I took an overdose")
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "overdose" in names

    def test_choking_flag(self):
        e = MedicalExtraction(symptoms=["choking"])
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "choking" in names

    def test_passed_out_flag(self):
        e = MedicalExtraction(chief_complaint="I passed out earlier")
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "passed out" in names

    def test_stroke_flag(self):
        e = MedicalExtraction(symptoms=["stroke"])
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "stroke" in names

    def test_kill_myself_flag(self):
        e = MedicalExtraction(chief_complaint="I want to kill myself")
        flags = detect_red_flags(e)
        names = [f.name for f in flags]
        assert "kill myself" in names


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

    def test_esi_1_heart_attack(self):
        e = MedicalExtraction(chief_complaint="I'm having a heart attack")
        flags = detect_red_flags(e)
        assert compute_acuity(e, flags) == 1

    def test_esi_1_dying(self):
        e = MedicalExtraction(chief_complaint="I'm dying")
        flags = detect_red_flags(e)
        assert compute_acuity(e, flags) == 1

    def test_esi_1_overdose(self):
        e = MedicalExtraction(chief_complaint="I took an overdose of pills")
        flags = detect_red_flags(e)
        assert compute_acuity(e, flags) == 1

    def test_esi_1_cardiac_arrest(self):
        e = MedicalExtraction(symptoms=["cardiac arrest"])
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

    def test_heart_attack_escalates(self):
        e = MedicalExtraction(chief_complaint="I'm having a heart attack")
        result = assess(e)
        assert result.acuity == 1
        assert result.escalate is True
        assert result.disposition == "escalate"

    def test_dying_escalates(self):
        e = MedicalExtraction(chief_complaint="I feel like I'm dying")
        result = assess(e)
        assert result.acuity == 1
        assert result.escalate is True

    def test_overdose_escalates(self):
        e = MedicalExtraction(chief_complaint="overdose")
        result = assess(e)
        assert result.acuity == 1
        assert result.escalate is True


# ---------------------------------------------------------------------------
# Risk signal evaluation tests
# ---------------------------------------------------------------------------

class TestRiskSignalEvaluation:
    """Tests for conviction-based risk signal evaluation."""

    def test_suicidal_ideation_true_triggers(self):
        """Self-harm phrase: suicidal_ideation=true should trigger escalation."""
        signals = RiskSignals(
            suicidal_ideation=True,
            suicidal_ideation_conviction=0.9,
            self_harm_intent=True,
            self_harm_intent_conviction=0.9,
        )
        triggered = evaluate_risk_signals(signals)
        flag_types = [t.flag_type for t in triggered]
        assert CriticalRedFlagType.SUICIDAL_IDEATION in flag_types
        assert CriticalRedFlagType.SELF_HARM in flag_types

    def test_chest_pain_and_cannot_breathe_triggers(self):
        """Chest pain + can't breathe should both trigger escalation."""
        signals = RiskSignals(
            chest_pain="yes",
            chest_pain_conviction=0.8,
            can_breathe="no",
            can_breathe_conviction=0.7,
        )
        triggered = evaluate_risk_signals(signals)
        flag_types = [t.flag_type for t in triggered]
        assert CriticalRedFlagType.CHEST_PAIN in flag_types
        assert CriticalRedFlagType.CANNOT_BREATHE in flag_types

    def test_neuro_deficit_triggers(self):
        """Neurological deficit should trigger escalation."""
        signals = RiskSignals(
            neuro_deficit="yes",
            neuro_deficit_conviction=0.8,
        )
        triggered = evaluate_risk_signals(signals)
        flag_types = [t.flag_type for t in triggered]
        assert CriticalRedFlagType.NEURO_DEFICIT in flag_types

    def test_low_conviction_suicidal_triggers(self):
        """Low conviction (0.25) for suicidal_ideation should still trigger (threshold 0.2)."""
        signals = RiskSignals(
            suicidal_ideation=False,
            suicidal_ideation_conviction=0.25,
        )
        triggered = evaluate_risk_signals(signals)
        flag_types = [t.flag_type for t in triggered]
        # Threshold is 0.2, so 0.25 should trigger
        assert CriticalRedFlagType.SUICIDAL_IDEATION in flag_types

    def test_safe_case_no_triggers(self):
        """All signals false/unknown with low convictions should NOT trigger."""
        signals = RiskSignals(
            suicidal_ideation=False,
            suicidal_ideation_conviction=0.1,
            self_harm_intent=False,
            self_harm_intent_conviction=0.1,
            homicidal_ideation=False,
            homicidal_ideation_conviction=0.1,
            can_breathe="yes",
            can_breathe_conviction=0.1,
            chest_pain="no",
            chest_pain_conviction=0.1,
            neuro_deficit="no",
            neuro_deficit_conviction=0.1,
            bleeding_uncontrolled="no",
            bleeding_uncontrolled_conviction=0.1,
        )
        triggered = evaluate_risk_signals(signals)
        assert len(triggered) == 0

    def test_homicidal_ideation_moderate_conviction_triggers(self):
        """Homicidal ideation with 0.45 conviction should trigger (threshold 0.4)."""
        signals = RiskSignals(
            homicidal_ideation=False,
            homicidal_ideation_conviction=0.45,
        )
        triggered = evaluate_risk_signals(signals)
        flag_types = [t.flag_type for t in triggered]
        assert CriticalRedFlagType.HOMICIDAL_IDEATION in flag_types

    def test_bleeding_uncontrolled_triggers(self):
        """Uncontrolled bleeding should trigger escalation."""
        signals = RiskSignals(
            bleeding_uncontrolled="yes",
            bleeding_uncontrolled_conviction=0.6,
        )
        triggered = evaluate_risk_signals(signals)
        flag_types = [t.flag_type for t in triggered]
        assert CriticalRedFlagType.BLEEDING_UNCONTROLLED in flag_types


class TestRiskSignalIntegration:
    """Tests for risk signals integrated with full assessment."""

    def test_risk_signals_cause_escalation(self):
        """Risk signals should cause escalation even with no keyword red flags."""
        e = MedicalExtraction(
            chief_complaint="feeling bad",
            risk_signals=RiskSignals(
                suicidal_ideation=True,
                suicidal_ideation_conviction=0.9,
            ),
        )
        result = assess(e)
        assert result.escalate is True
        assert len(result.triggered_risk_flags) > 0

    def test_escalated_includes_reason(self):
        """Escalated assessment should include human-readable reason."""
        e = MedicalExtraction(
            chief_complaint="want to end it",
            risk_signals=RiskSignals(
                suicidal_ideation=True,
                suicidal_ideation_conviction=0.95,
                self_harm_intent=True,
                self_harm_intent_conviction=0.9,
            ),
        )
        result = assess(e)
        assert result.escalate is True
        assert result.escalation_reason != ""
        assert "suicidal" in result.escalation_reason.lower() or "self-harm" in result.escalation_reason.lower()

    def test_risk_signals_bump_acuity(self):
        """Risk signal triggers should bump acuity to at least ESI-2."""
        e = MedicalExtraction(
            chief_complaint="headache",  # Would normally be ESI-5
            risk_signals=RiskSignals(
                suicidal_ideation=True,
                suicidal_ideation_conviction=0.9,
            ),
        )
        result = assess(e)
        assert result.acuity <= 2  # Should be bumped up due to risk signal

    def test_minor_concern_not_returned_when_escalated(self):
        """Ensure 'minor concern' language is never used when escalated."""
        e = MedicalExtraction(
            chief_complaint="small cut",
            symptoms=[],
            risk_signals=RiskSignals(
                chest_pain="yes",
                chest_pain_conviction=0.8,
            ),
        )
        result = assess(e)
        assert result.escalate is True
        # The assessment should indicate escalation, not "discharge"
        assert result.disposition == "escalate"

    def test_combined_keyword_and_risk_signals(self):
        """Both keyword red flags and risk signals should be counted."""
        e = MedicalExtraction(
            chief_complaint="chest pain",  # Keyword red flag
            symptoms=["shortness of breath"],  # Another keyword
            risk_signals=RiskSignals(
                chest_pain="yes",
                chest_pain_conviction=0.9,
                can_breathe="no",
                can_breathe_conviction=0.8,
            ),
        )
        result = assess(e)
        assert result.escalate is True
        assert result.acuity == 1  # Most critical
        # Should have both keyword flags and risk signal flags
        assert len(result.red_flags) >= 2
