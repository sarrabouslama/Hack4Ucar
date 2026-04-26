from app.modules.environment_infrastructure.models import EmailFootprintRequest, EmailMetricInput
from app.modules.environment_infrastructure.services import environment_scoring_service


def test_email_footprint_estimates_energy_and_co2():
    payload = EmailFootprintRequest(
        institution_id="ucar-fst",
        institution_name="FST",
        students_count=1800,
        employees_count=200,
        email_metrics=[
            EmailMetricInput(
                period_label="2026-S1",
                emails_sent=120000,
                average_email_size_kb=180,
                attachments_count=24000,
                average_attachment_size_kb=750,
                average_recipients=2.4,
                stored_days=180,
            )
        ],
    )

    result = environment_scoring_service.estimate_email_footprint(payload)

    assert result.total_emails_sent == 120000
    assert result.total_estimated_energy_kwh > 0
    assert result.total_estimated_co2_kg > 0
    assert len(result.period_breakdown) == 1


def test_email_footprint_flags_heavy_digital_usage():
    payload = EmailFootprintRequest(
        institution_id="ucar-heavy",
        institution_name="UCAR Heavy Mail",
        students_count=500,
        employees_count=50,
        email_metrics=[
            EmailMetricInput(
                period_label="2026-S1",
                emails_sent=900000,
                average_email_size_kb=950,
                attachments_count=500000,
                average_attachment_size_kb=4000,
                average_recipients=4.0,
                stored_days=365,
            )
        ],
    )

    result = environment_scoring_service.estimate_email_footprint(payload)

    assert result.verdict == "surconsommation numerique"
    assert result.annualized_co2_per_person_kg > 12
