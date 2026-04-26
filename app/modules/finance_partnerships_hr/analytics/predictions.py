"""
Budget and HR forecasting using Prophet.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import func

from app.core.database import SessionLocal
from app.modules.finance_partnerships_hr.db_models import Budget, Employee, FinancialReport, KpiMetric


def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _historical_budget_series(db_session, institution_id: Optional[str]) -> List[Tuple[datetime, float]]:
    series: List[Tuple[datetime, float]] = []
    metric_query = db_session.query(KpiMetric).filter(
        KpiMetric.indicator == "budget",
        KpiMetric.is_forecast.is_(False),
    )
    if institution_id:
        metric_query = metric_query.filter(KpiMetric.institution_id == institution_id)
    metric_rows = metric_query.order_by(KpiMetric.recorded_at.asc()).all()
    for row in metric_rows:
        series.append((row.recorded_at, _safe_float(row.metric_value)))
    if series:
        return series

    reports_query = db_session.query(FinancialReport).order_by(FinancialReport.report_date.asc())
    if institution_id:
        reports_query = reports_query.filter(FinancialReport.institution_id == institution_id)
    for report in reports_query.all():
        series.append((report.report_date, _safe_float(report.total_expenses)))
    if series:
        return series

    budget_rows = (
        db_session.query(Budget.fiscal_year, func.sum(Budget.spent_amount))
        .group_by(Budget.fiscal_year)
        .order_by(Budget.fiscal_year.asc())
        .all()
    )
    for year, spent in budget_rows:
        if year:
            series.append((datetime(int(year), 1, 1), _safe_float(spent)))
    return series


def _historical_headcount_series(db_session, institution_id: Optional[str]) -> List[Tuple[datetime, float]]:
    series: List[Tuple[datetime, float]] = []
    metric_query = db_session.query(KpiMetric).filter(
        KpiMetric.indicator == "headcount",
        KpiMetric.is_forecast.is_(False),
    )
    if institution_id:
        metric_query = metric_query.filter(KpiMetric.institution_id == institution_id)
    metric_rows = metric_query.order_by(KpiMetric.recorded_at.asc()).all()
    for row in metric_rows:
        series.append((row.recorded_at, _safe_float(row.metric_value)))
    if series:
        return series

    hires = (
        db_session.query(Employee.hire_date)
        .filter(Employee.hire_date.isnot(None))
        .order_by(Employee.hire_date.asc())
        .all()
    )
    running_total = 0
    for (hire_date,) in hires:
        running_total += 1
        series.append((datetime.combine(hire_date, datetime.min.time()), float(running_total)))
    return series


def _series_to_dataframe(series: List[Tuple[datetime, float]]) -> pd.DataFrame:
    if not series:
        return pd.DataFrame(columns=["ds", "y"])
    cleaned = [(moment, value) for moment, value in series if moment is not None]
    if len(cleaned) == 1:
        only_moment, only_value = cleaned[0]
        cleaned.append((only_moment + timedelta(days=30), only_value))
    df = pd.DataFrame(cleaned, columns=["ds", "y"])
    df["ds"] = pd.to_datetime(df["ds"])
    df["y"] = pd.to_numeric(df["y"], errors="coerce").fillna(0.0)
    return df.sort_values("ds")


def _extract_forecast_points(forecast_df: pd.DataFrame) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    today = datetime.utcnow().date()
    for horizon in (30, 90):
        target_date = today + timedelta(days=horizon)
        candidates = forecast_df.loc[forecast_df["ds"].dt.date >= target_date]
        row = candidates.iloc[0] if not candidates.empty else forecast_df.iloc[-1]
        output.append(
            {
                "horizon_days": horizon,
                "target_date": target_date.isoformat(),
                "predicted_value": _safe_float(row.get("yhat")),
                "lower_bound": _safe_float(row.get("yhat_lower")),
                "upper_bound": _safe_float(row.get("yhat_upper")),
            }
        )
    return output


def run_prophet_forecast(institution_id: Optional[str], indicator: str) -> Dict[str, Any]:
    indicator = indicator.lower().strip()
    if indicator not in {"budget", "headcount"}:
        return {"status": "error", "message": "indicator must be budget or headcount", "predictions": []}

    db_session = SessionLocal()
    try:
        if indicator == "budget":
            series = _historical_budget_series(db_session, institution_id)
            domain = "finance"
        else:
            series = _historical_headcount_series(db_session, institution_id)
            domain = "hr"

        df = _series_to_dataframe(series)
        if df.empty:
            return {"status": "error", "message": "No historical data for forecasting", "predictions": []}

        try:
            from prophet import Prophet  # type: ignore
        except Exception as exc:
            print(f"[ERROR] Prophet import failed: {exc}")
            return {"status": "error", "message": "Prophet is unavailable", "predictions": []}

        try:
            model = Prophet(daily_seasonality=False, weekly_seasonality=False, yearly_seasonality=True)
            model.fit(df)
            future = model.make_future_dataframe(periods=90)
            forecast = model.predict(future)
        except Exception as exc:
            print(f"[ERROR] Prophet forecasting failed: {exc}")
            return {"status": "error", "message": str(exc), "predictions": []}

        points = _extract_forecast_points(forecast)
        for point in points:
            record = KpiMetric(
                institution_id=institution_id,
                domain=domain,
                indicator=indicator,
                metric_value=point["predicted_value"],
                recorded_at=datetime.fromisoformat(point["target_date"] + "T00:00:00"),
                is_forecast=True,
                forecast_horizon_days=point["horizon_days"],
                lower_bound=point["lower_bound"],
                upper_bound=point["upper_bound"],
                source="prophet",
            )
            db_session.add(record)
        db_session.commit()

        return {"status": "success", "indicator": indicator, "predictions": points}
    except Exception as exc:
        db_session.rollback()
        print(f"[ERROR] Prediction pipeline failed: {exc}")
        return {"status": "error", "message": str(exc), "predictions": []}
    finally:
        db_session.close()


def get_predictions(institution_id: Optional[str], indicator: str) -> List[Dict[str, Any]]:
    db_session = SessionLocal()
    try:
        query = db_session.query(KpiMetric).filter(
            KpiMetric.indicator == indicator.lower().strip(),
            KpiMetric.is_forecast.is_(True),
        )
        if institution_id:
            query = query.filter(KpiMetric.institution_id == institution_id)
        rows = query.order_by(KpiMetric.recorded_at.desc()).limit(20).all()

        if not rows:
            result = run_prophet_forecast(institution_id=institution_id, indicator=indicator)
            return result.get("predictions", [])

        output: List[Dict[str, Any]] = []
        for row in rows:
            output.append(
                {
                    "indicator": row.indicator,
                    "institution_id": row.institution_id,
                    "predicted_value": _safe_float(row.metric_value),
                    "forecast_horizon_days": row.forecast_horizon_days,
                    "target_date": row.recorded_at.date().isoformat(),
                    "lower_bound": _safe_float(row.lower_bound),
                    "upper_bound": _safe_float(row.upper_bound),
                    "source": row.source,
                }
            )
        return output
    except Exception as exc:
        print(f"[ERROR] Fetching predictions failed: {exc}")
        return []
    finally:
        db_session.close()
