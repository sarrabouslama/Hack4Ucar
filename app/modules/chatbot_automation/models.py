"""Pydantic models for chatbot and automation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatContext(BaseModel):
    """Structured context passed to UniBot on each turn."""

    kpi_data: List[Dict[str, Any]] = Field(default_factory=list)
    document_excerpts: List[str] = Field(default_factory=list)
    recent_alerts: List[str] = Field(default_factory=list)
    reporting_period: Optional[str] = None
    current_date: Optional[str] = None
    extra_context: Dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Incoming chat request."""

    message: str
    user_id: str = "ucar-central"
    session_id: Optional[UUID] = None
    session_name: Optional[str] = None
    domain_context: Optional[str] = None
    context: ChatContext = Field(default_factory=ChatContext)


class ChatResponse(BaseModel):
    """Chat response returned to the client."""

    session_id: UUID
    answer: str
    model: str
    created_at: datetime
    used_context: bool
    requires_confirmation: bool = False
    suggested_action: Optional[str] = None


class ChatHistoryItem(BaseModel):
    """Serialized conversation turn."""

    user_message: str
    bot_response: str
    message_timestamp: datetime
    domain_context: Optional[str] = None


class ChatSessionResponse(BaseModel):
    """Session metadata with full history."""

    session_id: UUID
    user_id: str
    session_name: Optional[str] = None
    domain_context: Optional[str] = None
    status: str
    started_at: datetime
    history: List[ChatHistoryItem] = Field(default_factory=list)


class ChatSessionSummary(BaseModel):
    """Lightweight session card used in the sidebar listing."""

    session_id: UUID
    session_name: Optional[str] = None
    domain_context: Optional[str] = None
    status: str
    started_at: datetime
    message_count: int = 0
    last_message_at: Optional[datetime] = None