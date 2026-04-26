"""
Business logic for environment and infrastructure
"""

from collections import defaultdict
from typing import Dict, List

from app.modules.environment_infrastructure.models import (
    ConsumptionBreakdown,
    EmailFootprintRequest,
    EmailFootprintResponse,
    EmailPeriodEstimate,
    EnvironmentalScorecardResponse,
    InstitutionScorecardRequest,
    RSEInitiativeAssessment,
    TimeSeriesPoint,
)


class EnvironmentScoringService:
    """Rule-based environmental scoring engine for university institutions."""

    _EMISSION_FACTORS = {
        "electricity": {"kwh": 0.43},
        "gas": {"kwh": 0.23, "m3": 2.05},
        "water": {"m3": 0.298},
    }
    _BENCHMARK_PER_PERSON_KG = 420.0
    _DIGITAL_GRID_CO2_KG_PER_KWH = 0.43
    _DATA_TRANSFER_KWH_PER_GB = 0.06
    _STORAGE_KWH_PER_GB_DAY = 0.00005
    _EMAIL_BENCHMARK_PER_PERSON_KG = 12.0
    _BASE_EMAIL_CO2_KG = 0.004
    _ATTACHMENT_EMAIL_CO2_KG = 0.025

    def build_scorecard(self, payload: InstitutionScorecardRequest) -> EnvironmentalScorecardResponse:
        """Aggregate utilities and RSE actions into a single environmental KPI."""

        total_people = max(payload.students_count + payload.employees_count, 1)
        gross_breakdown = self._compute_breakdown(payload, total_people)
        gross_co2_kg = sum(item.co2_kg for item in gross_breakdown)

        rse_assessments = [
            self._assess_rse_initiative(initiative) for initiative in payload.rse_initiatives
        ]
        total_rse_reduction_kg = sum(item.estimated_reduction_kg for item in rse_assessments)
        optimized_co2_kg = max(gross_co2_kg - total_rse_reduction_kg, 0.0)

        co2_per_person_kg = gross_co2_kg / total_people
        annualization_factor = self._estimate_annualization_factor(payload)
        annualized_co2_per_person_kg = co2_per_person_kg * annualization_factor
        verdict = self._build_verdict(annualized_co2_per_person_kg)
        subdimension_scores = self._build_subdimension_scores(
            co2_per_person_kg=annualized_co2_per_person_kg,
            benchmark=self._BENCHMARK_PER_PERSON_KG,
            rse_assessments=rse_assessments,
            utility_count=len(payload.utility_bills),
        )
        environmental_score = round(
            0.5 * subdimension_scores["consumption_efficiency"]
            + 0.3 * subdimension_scores["rse_maturity"]
            + 0.2 * subdimension_scores["data_reliability"],
            2,
        )

        timeline = self._build_timeline(payload, total_people, rse_assessments)
        insights = self._build_insights(payload.institution_name, total_people, gross_breakdown, rse_assessments)

        return EnvironmentalScorecardResponse(
            institution_id=payload.institution_id,
            institution_name=payload.institution_name,
            total_people=total_people,
            gross_co2_kg=round(gross_co2_kg, 2),
            optimized_co2_kg=round(optimized_co2_kg, 2),
            co2_per_person_kg=round(co2_per_person_kg, 2),
            annualized_co2_per_person_kg=round(annualized_co2_per_person_kg, 2),
            benchmark_per_person_kg=self._BENCHMARK_PER_PERSON_KG,
            verdict=verdict,
            environmental_score=environmental_score,
            subdimension_scores=subdimension_scores,
            total_rse_reduction_kg=round(total_rse_reduction_kg, 2),
            breakdown=gross_breakdown,
            rse_assessments=rse_assessments,
            timeline=timeline,
            insights=insights,
        )

    def estimate_email_footprint(self, payload: EmailFootprintRequest) -> EmailFootprintResponse:
        """Estimate digital-energy and CO2 impact from email metadata only."""

        total_people = max(payload.students_count + payload.employees_count, 1)
        annualization_factor = self._estimate_period_annualization(
            [metric.period_label for metric in payload.email_metrics]
        )
        period_breakdown: List[EmailPeriodEstimate] = []

        total_emails_sent = 0
        total_energy_kwh = 0.0
        total_co2_kg = 0.0

        for metric in payload.email_metrics:
            payload_gb = (
                metric.emails_sent * metric.average_email_size_kb
                + metric.attachments_count * metric.average_attachment_size_kb
            ) / (1024 * 1024)
            delivery_multiplier = max(metric.average_recipients, 1.0)
            transfer_energy_kwh = payload_gb * delivery_multiplier * self._DATA_TRANSFER_KWH_PER_GB
            storage_energy_kwh = payload_gb * metric.stored_days * self._STORAGE_KWH_PER_GB_DAY
            base_email_energy_kwh = metric.emails_sent * 0.0003
            attachment_energy_kwh = metric.attachments_count * 0.002
            estimated_energy_kwh = (
                transfer_energy_kwh + storage_energy_kwh + base_email_energy_kwh + attachment_energy_kwh
            )
            energy_model_co2_kg = estimated_energy_kwh * self._DIGITAL_GRID_CO2_KG_PER_KWH
            attachment_ratio = (metric.attachments_count / metric.emails_sent) if metric.emails_sent else 0.0
            heuristic_co2_kg = metric.emails_sent * metric.average_recipients * (
                self._BASE_EMAIL_CO2_KG + attachment_ratio * self._ATTACHMENT_EMAIL_CO2_KG
            )
            size_multiplier = 1.0 + min(metric.average_email_size_kb / 5120, 1.5)
            estimated_co2_kg = max(energy_model_co2_kg, heuristic_co2_kg * size_multiplier)

            total_emails_sent += metric.emails_sent
            total_energy_kwh += estimated_energy_kwh
            total_co2_kg += estimated_co2_kg

            period_breakdown.append(
                EmailPeriodEstimate(
                    period_label=metric.period_label,
                    emails_sent=metric.emails_sent,
                    estimated_energy_kwh=round(estimated_energy_kwh, 4),
                    estimated_co2_kg=round(estimated_co2_kg, 4),
                    average_recipients=metric.average_recipients,
                    attachment_ratio=round(attachment_ratio, 4),
                )
            )

        annualized_co2_per_person_kg = (total_co2_kg / total_people) * annualization_factor
        verdict = self._build_email_verdict(annualized_co2_per_person_kg)
        digital_responsibility_score = round(
            max(
                0.0,
                min(
                    100.0,
                    100 - ((annualized_co2_per_person_kg / self._EMAIL_BENCHMARK_PER_PERSON_KG) - 0.5) * 70,
                ),
            ),
            2,
        )

        return EmailFootprintResponse(
            institution_id=payload.institution_id,
            institution_name=payload.institution_name,
            total_people=total_people,
            total_emails_sent=total_emails_sent,
            total_estimated_energy_kwh=round(total_energy_kwh, 4),
            total_estimated_co2_kg=round(total_co2_kg, 4),
            annualized_co2_per_person_kg=round(annualized_co2_per_person_kg, 4),
            digital_responsibility_score=digital_responsibility_score,
            verdict=verdict,
            methodology=[
                "Aucune lecture du contenu email: seulement des metriques techniques.",
                "Energie estimee a partir du volume transfere, des destinataires, des pieces jointes et du stockage.",
                "Conversion CO2 via un facteur carbone simplifie du mix electrique.",
            ],
            period_breakdown=period_breakdown,
        )

    def _compute_breakdown(
        self,
        payload: InstitutionScorecardRequest,
        total_people: int,
    ) -> List[ConsumptionBreakdown]:
        grouped_consumption: Dict[str, float] = defaultdict(float)
        grouped_co2: Dict[str, float] = defaultdict(float)
        normalized_units: Dict[str, str] = {}

        for bill in payload.utility_bills:
            emission_factor = self._EMISSION_FACTORS[bill.utility_type][bill.consumption_unit]
            co2_kg = bill.consumption_value * emission_factor
            grouped_consumption[bill.utility_type] += bill.consumption_value
            grouped_co2[bill.utility_type] += co2_kg
            normalized_units[bill.utility_type] = bill.consumption_unit

        total_co2 = sum(grouped_co2.values()) or 1.0
        breakdown: List[ConsumptionBreakdown] = []
        for utility_type in sorted(grouped_co2.keys()):
            co2_kg = grouped_co2[utility_type]
            breakdown.append(
                ConsumptionBreakdown(
                    utility_type=utility_type,
                    total_consumption=round(grouped_consumption[utility_type], 2),
                    normalized_unit=normalized_units[utility_type],
                    co2_kg=round(co2_kg, 2),
                    share_percent=round((co2_kg / total_co2) * 100, 2),
                    intensity_per_person_kg=round(co2_kg / total_people, 2),
                    intensity_per_m2_kg=round(co2_kg / payload.surface_m2, 4),
                )
            )
        return breakdown

    def _estimate_annualization_factor(self, payload: InstitutionScorecardRequest) -> float:
        """Infer how many times the observed period should be projected to cover a full year."""

        period_labels = {bill.period_label.upper() for bill in payload.utility_bills}
        return self._estimate_period_annualization(list(period_labels))

    def _estimate_period_annualization(self, period_labels: List[str]) -> float:
        """Infer how many times the observed period should be projected to cover a full year."""

        period_labels = {label.upper() for label in period_labels}
        if not period_labels:
            return 1.0
        if all("-S" in label for label in period_labels):
            return 2.0
        if all("-Q" in label for label in period_labels):
            return 4.0
        if all(len(label) == 7 and label[4] == "-" for label in period_labels):
            return 12.0
        return 1.0

    def _assess_rse_initiative(self, initiative) -> RSEInitiativeAssessment:
        reliability_status = (
            "fiable"
            if initiative.proof_document_present and initiative.proof_confidence >= 0.65
            else "a_verifier"
        )
        confidence = initiative.proof_confidence if initiative.proof_document_present else 0.25
        weighted_reduction = initiative.estimated_co2_reduction_kg * (
            1.0 if reliability_status == "fiable" else 0.45
        )
        return RSEInitiativeAssessment(
            title=initiative.title,
            category=initiative.category,
            reliability_status=reliability_status,
            estimated_reduction_kg=round(weighted_reduction, 2),
            confidence=round(confidence, 2),
        )

    def _build_verdict(self, co2_per_person_kg: float) -> str:
        if co2_per_person_kg <= self._BENCHMARK_PER_PERSON_KG * 0.8:
            return "consommation optimale"
        if co2_per_person_kg <= self._BENCHMARK_PER_PERSON_KG * 1.1:
            return "dans la norme"
        return "surconsommation detectee"

    def _build_email_verdict(self, annualized_co2_per_person_kg: float) -> str:
        if annualized_co2_per_person_kg <= self._EMAIL_BENCHMARK_PER_PERSON_KG * 0.8:
            return "usage numerique sobre"
        if annualized_co2_per_person_kg <= self._EMAIL_BENCHMARK_PER_PERSON_KG * 1.15:
            return "usage numerique modere"
        return "surconsommation numerique"

    def _build_subdimension_scores(
        self,
        co2_per_person_kg: float,
        benchmark: float,
        rse_assessments: List[RSEInitiativeAssessment],
        utility_count: int,
    ) -> dict[str, float]:
        consumption_efficiency = max(
            0.0,
            min(100.0, 100 - ((co2_per_person_kg / benchmark) - 0.7) * 85),
        )
        reliable_actions = [item for item in rse_assessments if item.reliability_status == "fiable"]
        rse_maturity = min(
            100.0,
            len(rse_assessments) * 12 + sum(item.estimated_reduction_kg for item in reliable_actions) / 25,
        )
        reliability_ratio = len(reliable_actions) / len(rse_assessments) if rse_assessments else 0.5
        data_reliability = min(100.0, 45 + reliability_ratio * 35 + utility_count * 5)
        return {
            "consumption_efficiency": round(consumption_efficiency, 2),
            "rse_maturity": round(rse_maturity, 2),
            "data_reliability": round(data_reliability, 2),
        }

    def _build_timeline(
        self,
        payload: InstitutionScorecardRequest,
        total_people: int,
        rse_assessments: List[RSEInitiativeAssessment],
    ) -> List[TimeSeriesPoint]:
        period_to_co2: Dict[str, float] = defaultdict(float)
        for bill in payload.utility_bills:
            factor = self._EMISSION_FACTORS[bill.utility_type][bill.consumption_unit]
            period_to_co2[bill.period_label] += bill.consumption_value * factor

        reliable_rse_total = sum(item.estimated_reduction_kg for item in rse_assessments)
        periods = sorted(period_to_co2.keys())
        reduction_step = reliable_rse_total / len(periods) if periods else 0.0
        cumulative_reduction = 0.0

        timeline: List[TimeSeriesPoint] = []
        for period in periods:
            gross_co2 = period_to_co2[period]
            cumulative_reduction += reduction_step
            optimized_co2 = max(gross_co2 - cumulative_reduction, 0.0)
            verdict = self._build_verdict(gross_co2 / total_people)
            timeline.append(
                TimeSeriesPoint(
                    period_label=period,
                    gross_co2_kg=round(gross_co2, 2),
                    optimized_co2_kg=round(optimized_co2, 2),
                    verdict=verdict,
                )
            )
        return timeline

    def _build_insights(
        self,
        institution_name: str,
        total_people: int,
        gross_breakdown: List[ConsumptionBreakdown],
        rse_assessments: List[RSEInitiativeAssessment],
    ) -> List[str]:
        if not gross_breakdown:
            return [f"Aucune consommation exploitable n'a ete detectee pour {institution_name}."]

        top_utility = max(gross_breakdown, key=lambda item: item.co2_kg)
        total_gross = sum(item.co2_kg for item in gross_breakdown)
        reliable_count = sum(1 for item in rse_assessments if item.reliability_status == "fiable")
        verdict = self._build_verdict(total_gross / total_people)
        return [
            f"Le poste le plus emissif est {top_utility.utility_type} avec {top_utility.share_percent}% du CO2 brut.",
            f"{reliable_count} acte(s) RSE sont juges fiables et integrables dans le CO2 optimise.",
            f"Le moteur classe actuellement l'institution en '{verdict}'.",
        ]


environment_scoring_service = EnvironmentScoringService()
