"""API routes for chatbot and automation."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
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
    """List all chat sessions for a given user."""

    return chatbot_service.list_sessions(db, user_id)


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(session_id: UUID, db: Session = Depends(get_db)):
    """Fetch a persisted chat session and its history."""

    return chatbot_service.get_session(db, session_id)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_session(session_id: UUID, db: Session = Depends(get_db)):
    """Soft-delete a chat session."""

    chatbot_service.end_session(db, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
