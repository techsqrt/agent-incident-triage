"""Tests for medical triage Pydantic schemas."""

import pytest
from pydantic import ValidationError

from services.api.src.api.domains.medical.schemas import (
    MedicalAssessment,
    MedicalExtraction,
    RedFlag,
    VitalSigns,
)


class TestVitalSigns:
    def test_defaults_all_none(self):
        v = VitalSigns()
        assert v.heart_rate is None
        assert v.blood_pressure_systolic is None
        assert v.oxygen_saturation is None

    def test_valid_vitals(self):
        v = VitalSigns(heart_rate=80, oxygen_saturation=98, temperature_f=98.6)
        assert v.heart_rate == 80
        assert v.oxygen_saturation == 98

    def test_hr_out_of_range(self):
        with pytest.raises(ValidationError):
            VitalSigns(heart_rate=400)

    def test_spo2_out_of_range(self):
        with pytest.raises(ValidationError):
            VitalSigns(oxygen_saturation=105)

    def test_temp_out_of_range(self):
        with pytest.raises(ValidationError):
            VitalSigns(temperature_f=120.0)


class TestMedicalExtraction:
    def test_minimal_extraction(self):
        e = MedicalExtraction()
        assert e.chief_complaint == ""
        assert e.symptoms == []
        assert e.pain_scale is None
        assert e.mental_status == "alert"

    def test_full_extraction(self):
        e = MedicalExtraction(
            chief_complaint="chest pain",
            symptoms=["chest pain", "shortness of breath"],
            pain_scale=7,
            vitals=VitalSigns(heart_rate=110, oxygen_saturation=93),
            medical_history=["hypertension"],
            allergies=["penicillin"],
            medications=["lisinopril"],
            onset="2 hours ago",
            mental_status="alert",
        )
        assert e.chief_complaint == "chest pain"
        assert len(e.symptoms) == 2
        assert e.vitals.heart_rate == 110

    def test_pain_scale_validation(self):
        with pytest.raises(ValidationError):
            MedicalExtraction(pain_scale=11)

    def test_pain_scale_zero_valid(self):
        e = MedicalExtraction(pain_scale=0)
        assert e.pain_scale == 0


class TestMedicalAssessment:
    def test_assessment_fields(self):
        a = MedicalAssessment(
            acuity=2,
            escalate=True,
            red_flags=[RedFlag(name="chest pain", reason="Possible cardiac")],
            disposition="escalate",
            summary="ESI-2 | ESCALATE",
        )
        assert a.acuity == 2
        assert a.escalate is True
        assert len(a.red_flags) == 1

    def test_acuity_out_of_range(self):
        with pytest.raises(ValidationError):
            MedicalAssessment(acuity=0)
        with pytest.raises(ValidationError):
            MedicalAssessment(acuity=6)
