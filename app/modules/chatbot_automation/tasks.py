"""Celery tasks for chatbot automation."""

import os
from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.modules.chatbot_automation.db_models import MailLog
from app.modules.finance_partnerships_hr.db_models import Budget
from app.modules.kpis.db_models import Alert, Institution


@celery_app.task(name="app.modules.chatbot_automation.tasks.detect_dropout_anomalies")
def detect_dropout_anomalies():
    """
    Task to detect dropout rate anomalies and create proposed mail logs.
    Fetches real active alerts from the database.
    """
    db = SessionLocal()
    try:
        # Fetch active alerts from the database
        db_alerts = db.query(Alert).filter(Alert.status == "active").all()
        
        created_logs = []
        for alert in db_alerts:
            # Check if we already have a mail log for this alert to avoid duplicates
            existing = db.query(MailLog).filter(
                MailLog.anomaly_details["alert_id"].astext == str(alert.id)
            ).first()
            
            if existing:
                continue

            # Find the institution contact email
            institution = db.query(Institution).filter(Institution.id == alert.institution_id).first()
            recipient = institution.contact_email if institution and institution.contact_email else "admin@ucar.tn"

            log = MailLog(
                anomaly_type=alert.severity if alert.severity else "critical_kpi",
                anomaly_details={
                    "alert_id": str(alert.id),
                    "title": alert.title,
                    "message": alert.message,
                    "institution": institution.name if institution else "Unknown",
                    "actual_value": alert.actual_value,
                    "threshold": alert.threshold_value,
                    "xai_explanation": alert.xai_explanation
                },
                recipient_email=recipient,
                status="proposed",
            )
            db.add(log)
            created_logs.append(log)
        
        db.commit()
        return f"Converted {len(created_logs)} database alerts to mailing workflows"
    finally:
        db.close()


@celery_app.task(name="app.modules.chatbot_automation.tasks.send_anomaly_email")
def send_anomaly_email(mail_log_id: str):
    """
    Task to send the proposed email.
    """
    db = SessionLocal()
    try:
        log = db.query(MailLog).filter(MailLog.id == mail_log_id).first()
        if not log:
            return "Log not found"

        # Mocking SMTP send logic
        print(f"Sending email to {log.recipient_email}...")
        print(f"Subject: {log.subject}")
        print(f"Body: {log.body_plan}")

        log.status = "sent"
        log.sent_at = datetime.utcnow()
        db.commit()
        
        return f"Email sent to {log.recipient_email}"
    except Exception as e:
        if log:
            log.status = "failed"
            log.error_message = str(e)
            db.commit()
        return f"Failed to send email: {e}"
    finally:
        db.close()
