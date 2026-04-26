"""
Prediction Service - Prophet-based KPI predictions
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from uuid import UUID

import pandas as pd
import numpy as np
from prophet import Prophet

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.kpi_models import KPIMetric, KPIPrediction, KPI_DOMAIN, KPI_PERIOD


class PredictionService:
    """Service for KPI predictions using Prophet"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _prepare_prophet_data(self, kpis: List[KPIMetric]) -> pd.DataFrame:
        """Convert KPIs to Prophet format (ds, y)"""
        if not kpis:
            return pd.DataFrame()
        
        data = []
        for kpi in kpis:
            data.append({
                "ds": kpi.reporting_date,
                "y": kpi.value
            })
        
        df = pd.DataFrame(data)
        df = df.sort_values("ds")
        return df
    
    def predict_kpi(
        self,
        institution_id: UUID,
        domain: str,
        indicator: str,
        horizon_days: int = 30
    ) -> Dict[str, Any]:
        """Generate predictions for a specific KPI"""
        # Get historical data
        kpis = self.db.query(KPIMetric).filter(
            and_(
                KPIMetric.institution_id == institution_id,
                KPIMetric.domain == KPI_DOMAIN(domain),
                KPIMetric.indicator == indicator
            )
        ).order_by(KPIMetric.reporting_date.asc()).all()
        
        if len(kpis) < 3:
            return {
                "error": "Insufficient data for prediction (minimum 3 data points required)",
                "data_points": len(kpis)
            }
        
        # Prepare data for Prophet
        df = self._prepare_prophet_data(kpis)
        
        # Train Prophet model
        model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            changepoint_prior_scale=0.05
        )
        model.fit(df)
        
        # Make future dataframe
        future = model.make_future_dataframe(periods=horizon_days)
        forecast = model.predict(future)
        
        # Get the last prediction (horizon date)
        last_prediction = forecast.iloc[-1]
        
        # Store prediction in database
        prediction = KPIPrediction(
            kpi_metric_id=kpis[-1].id,
            prediction_date=last_prediction["ds"],
            predicted_value=last_prediction["yhat"],
            confidence_lower=last_prediction["yhat_lower"],
            confidence_upper=last_prediction["yhat_upper"],
            model_type="prophet",
            horizon_days=horizon_days
        )
        self.db.add(prediction)
        self.db.commit()
        
        # Return forecast data
        forecast_data = forecast.tail(horizon_days + 1)[[
            "ds", "yhat", "yhat_lower", "yhat_upper"
        ]].to_dict("records")
        
        return {
            "institution_id": str(institution_id),
            "domain": domain,
            "indicator": indicator,
            "horizon_days": horizon_days,
            "last_prediction": {
                "date": last_prediction["ds"].isoformat(),
                "predicted_value": round(last_prediction["yhat"], 2),
                "confidence_lower": round(last_prediction["yhat_lower"], 2),
                "confidence_upper": round(last_prediction["yhat_upper"], 2)
            },
            "forecast": [
                {
                    "date": f["ds"].isoformat(),
                    "predicted_value": round(f["yhat"], 2),
                    "lower": round(f["yhat_lower"], 2),
                    "upper": round(f["yhat_upper"], 2)
                }
                for f in forecast_data
            ],
            "model_info": {
                "data_points": len(kpis),
                "date_range": {
                    "start": kpis[0].reporting_date.isoformat(),
                    "end": kpis[-1].reporting_date.isoformat()
                }
            }
        }
    
    def predict_all_domains(
        self,
        institution_id: UUID,
        horizon_days: int = 30
    ) -> Dict[str, Any]:
        """Generate predictions for all KPIs of an institution"""
        predictions = {}
        
        # Get all unique domain/indicator combinations
        kpis = self.db.query(KPIMetric).filter(
            KPIMetric.institution_id == institution_id
        ).all()
        
        # Group by domain/indicator
        kpi_groups = {}
        for kpi in kpis:
            key = (kpi.domain.value, kpi.indicator)
            if key not in kpi_groups:
                kpi_groups[key] = []
            kpi_groups[key].append(kpi)
        
        # Generate predictions for each group
        for (domain, indicator), group_kpis in kpi_groups.items():
            if len(group_kpis) >= 3:
                result = self.predict_kpi(
                    institution_id,
                    domain,
                    indicator,
                    horizon_days
                )
                if "error" not in result:
                    predictions[f"{domain}_{indicator}"] = result
        
        return {
            "institution_id": str(institution_id),
            "horizon_days": horizon_days,
            "predictions": predictions,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    def get_prediction(
        self,
        kpi_metric_id: UUID,
        horizon_days: int = None
    ) -> Optional[KPIPrediction]:
        """Get stored prediction for a KPI"""
        query = self.db.query(KPIPrediction).filter(
            KPIPrediction.kpi_metric_id == kpi_metric_id
        )
        
        if horizon_days:
            query = query.filter(KPIPrediction.horizon_days == horizon_days)
        
        return query.order_by(KPIPrediction.created_at.desc()).first()
    
    def compare_with_prediction(
        self,
        institution_id: UUID,
        domain: str,
        indicator: str
    ) -> Dict[str, Any]:
        """Compare actual KPI values with predictions"""
        # Get actual recent values
        actual_kpis = self.db.query(KPIMetric).filter(
            and_(
                KPIMetric.institution_id == institution_id,
                KPIMetric.domain == KPI_DOMAIN(domain),
                KPIMetric.indicator == indicator
            )
        ).order_by(KPIMetric.reporting_date.desc()).limit(5).all()
        
        if not actual_kpis:
            return {"error": "No actual data found"}
        
        # Get predictions
        predictions = self.db.query(KPIPrediction).join(KPIMetric).filter(
            and_(
                KPIMetric.institution_id == institution_id,
                KPIMetric.domain == KPI_DOMAIN(domain),
                KPIMetric.indicator == indicator
            )
        ).order_by(KPIPrediction.prediction_date.desc()).limit(5).all()
        
        comparison = []
        for actual, predicted in zip(actual_kpis, predictions):
            error = actual.value - predicted.predicted_value
            error_pct = (error / predicted.predicted_value * 100) if predicted.predicted_value != 0 else 0
            
            comparison.append({
                "date": actual.reporting_date.isoformat(),
                "actual_value": actual.value,
                "predicted_value": predicted.predicted_value,
                "error": round(error, 2),
                "error_percentage": round(error_pct, 2)
            })
        
        return {
            "domain": domain,
            "indicator": indicator,
            "comparison": comparison
        }