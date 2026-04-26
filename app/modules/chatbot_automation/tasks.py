"""Celery tasks for chatbot automation."""

import os
from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.modules.chatbot_automation.db_models import MailLog
from app.modules.education_research.db_models import Student


@celery_app.task(name="app.modules.chatbot_automation.tasks.detect_dropout_anomalies")
def detect_dropout_anomalies():
    """
    Task to detect dropout rate anomalies and create proposed mail logs.
    In a real scenario, this would query student data and calculate rates.
    """
    db = SessionLocal()
    try:
        # Mocking anomaly detection for the demo
        # Imagine we found 3 institutions with high dropout rates
        anomalies = [
            {
                "institution": "Polytechnique School",
                "dropout_rate": 0.15,
                "director_email": "director@poly.edu",
            },
            {
                "institution": "Medical Faculty",
                "dropout_rate": 0.22,
                "director_email": "dean@med.edu",
            },
            {
                "institution": "Business School",
                "dropout_rate": 0.18,
                "director_email": "admin@business.edu",
            },
        ]

        created_logs = []
        for anomaly in anomalies:
            log = MailLog(
                anomaly_type="dropout_rate",
                anomaly_details=anomaly,
                recipient_email=anomaly["director_email"],
                status="proposed",
            )
            db.add(log)
            created_logs.append(log)
        
        db.commit()
        return f"Detected {len(anomalies)} anomalies"
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
