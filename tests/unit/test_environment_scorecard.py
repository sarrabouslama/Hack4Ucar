from app.modules.environment_infrastructure.models import (
    InstitutionScorecardRequest,
    RSEInitiativeInput,
    UtilityBillInput,
)
from app.modules.environment_infrastructure.services import environment_scoring_service


def test_environmental_scorecard_flags_overconsumption():
    payload = InstitutionScorecardRequest(
        institution_id="ucar-fst",
        institution_name="FST",
        surface_m2=12000,
        students_count=1800,
        employees_count=220,
        utility_bills=[
            UtilityBillInput(
                utility_type="electricity",
                period_label="2026-S1",
                consumption_value=980000,
                consumption_unit="kwh",
                invoice_amount=240000,
            ),
            UtilityBillInput(
                utility_type="gas",
                period_label="2026-S1",
                consumption_value=42000,
                consumption_unit="m3",
                invoice_amount=30000,
            ),
            UtilityBillInput(
                utility_type="water",
                period_label="2026-S1",
                consumption_value=15000,
                consumption_unit="m3",
                invoice_amount=16000,
            ),
        ],
        rse_initiatives=[
            RSEInitiativeInput(
                title="Solar parking shade",
                category="solar",
                description="Installation de panneaux solaires sur le parking",
                estimated_co2_reduction_kg=38000,
                proof_document_present=True,
                proof_confidence=0.92,
            )
        ],
    )

    result = environment_scoring_service.build_scorecard(payload)

    assert result.verdict == "surconsommation detectee"
    assert result.optimized_co2_kg < result.gross_co2_kg
    assert result.breakdown[0].utility_type == "electricity"
    assert result.total_rse_reduction_kg == 38000


def test_environmental_scorecard_marks_unverified_rse_with_discount():
    payload = InstitutionScorecardRequest(
        institution_id="ucar-esiat",
        institution_name="ESIAT",
        surface_m2=5000,
        students_count=600,
        employees_count=100,
        utility_bills=[
            UtilityBillInput(
                utility_type="electricity",
                period_label="2026-S1",
                consumption_value=180000,
                consumption_unit="kwh",
            )
        ],
        rse_initiatives=[
            RSEInitiativeInput(
                title="LED retrofit",
                category="lighting",
                description="Remplacement de l'eclairage classique par des LED",
                estimated_co2_reduction_kg=10000,
                proof_document_present=False,
                proof_confidence=0.0,
            )
        ],
    )

    result = environment_scoring_service.build_scorecard(payload)

    assert result.rse_assessments[0].reliability_status == "a_verifier"
    assert result.total_rse_reduction_kg == 4500
    assert len(result.timeline) == 1
