"""
Database models for chatbot and automation
"""

from sqlalchemy import Column, String, DateTime, Text, Boolean, JSON
from sqlalchemy import Uuid as UUID
from datetime import datetime

from app.core.models import BaseModel


class ChatSession(BaseModel):
    """Chat session model"""

    __tablename__ = "chat_sessions"

    user_id = Column(String(255), nullable=False)
    session_name = Column(String(255), nullable=True)
    status = Column(String(50), default="active", nullable=False)
    domain_context = Column(String(100), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ended_at = Column(DateTime, nullable=True)


class ChatMessage(BaseModel):
    """Chat message model"""

    __tablename__ = "chat_messages"

    session_id = Column(UUID(as_uuid=True), nullable=False)
    user_message = Column(Text, nullable=False)
    bot_response = Column(Text, nullable=False)
    message_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    domain_context = Column(String(100), nullable=True)
    confidence_score = Column(String(10), nullable=True)


class AutomationAction(BaseModel):
    """Automation action model"""

    __tablename__ = "automation_actions"

    action_name = Column(String(255), nullable=False)
    domain = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    action_type = Column(String(100), nullable=False)
    parameters = Column(JSON, nullable=True)
    enabled = Column(Boolean, default=True)


class Workflow(BaseModel):
    """Workflow model"""

    __tablename__ = "workflows"

    workflow_name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    workflow_type = Column(String(100), nullable=False)  # optimization, orchestration, etc.
    status = Column(String(50), default="active", nullable=False)
    steps = Column(JSON, nullable=False)
    enabled = Column(Boolean, default=True)


class WorkflowExecution(BaseModel):
    """Workflow execution model"""

    __tablename__ = "workflow_executions"

    workflow_id = Column(UUID(as_uuid=True), nullable=False)
    execution_status = Column(String(50), nullable=False)  # running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)


class Orchestration(BaseModel):
    """Executive orchestration model"""

    __tablename__ = "orchestrations"

    orchestration_name = Column(String(255), nullable=False)
    involved_domains = Column(JSON, nullable=False)  # list of domains
    coordination_level = Column(String(50), nullable=False)
    status = Column(String(50), default="inactive", nullable=False)
    last_executed = Column(DateTime, nullable=True)
    next_scheduled = Column(DateTime, nullable=True)


class MailLog(BaseModel):
    """Mail logs for automated workflows"""

    __tablename__ = "mail_logs"

    anomaly_type = Column(String(100), nullable=False)  # e.g., dropout_rate
    anomaly_details = Column(JSON, nullable=False)
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    body_plan = Column(Text, nullable=True)  # Proposed draft
    status = Column(String(50), default="proposed", nullable=False)  # proposed, confirmed, sent, failed
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
