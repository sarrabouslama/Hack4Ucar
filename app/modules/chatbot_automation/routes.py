"""API routes for chatbot and automation."""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.chatbot_automation.models import (
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    ChatSessionSummary,
)
from app.modules.chatbot_automation.services import chatbot_service

router = APIRouter()


@router.get("/health")
async def chatbot_health():
    """Basic health endpoint for the chatbot module."""
    return {"module": "chatbot_automation", "status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Send a UCAR chat message to UniBot."""
    return chatbot_service.chat(db, request)


@router.get("/sessions", response_model=List[ChatSessionSummary])
async def list_sessions(user_id: str = "ucar-central", db: Session = Depends(get_db)):
    """List all chat sessions for a given user (most recent first)."""
    return chatbot_service.list_sessions(db, user_id)


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(session_id: UUID, db: Session = Depends(get_db)):
    """Fetch a persisted chat session and its history."""
    return chatbot_service.get_session(db, session_id)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_chat_session(session_id: UUID, db: Session = Depends(get_db)):
    """Soft-delete (end) a chat session."""
    chatbot_service.end_session(db, session_id)


# ──────────────────────────────────────────────────────────────────────────
# Automation & Mailing Routes
# ──────────────────────────────────────────────────────────────────────────

@router.get("/mail-logs")
async def list_mail_logs(status: Optional[str] = None, db: Session = Depends(get_db)):
    """List all detected anomalies and mail logs."""
    return chatbot_service.list_mail_logs(db, status)


@router.post("/detect-anomalies")
async def detect_anomalies(db: Session = Depends(get_db)):
    """Trigger the anomaly detection workflow."""
    message = await chatbot_service.run_detection(db)
    return {"message": message}


@router.post("/propose-draft/{mail_log_id}")
async def propose_draft(mail_log_id: UUID, db: Session = Depends(get_db)):
    """Generate an AI draft for a mail log."""
    return await chatbot_service.propose_email_draft(db, mail_log_id)


@router.post("/confirm-send/{mail_log_id}")
async def confirm_send(mail_log_id: UUID, db: Session = Depends(get_db)):
    """Confirm and send the email via background task."""
    message = chatbot_service.confirm_and_send(db, mail_log_id)
    return {"message": message}