"""Business logic for chatbot and automation."""

from __future__ import annotations

from datetime import datetime
import json
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.modules.chatbot_automation.db_models import ChatMessage, ChatSession
from app.modules.chatbot_automation.models import (
    ChatContext,
    ChatHistoryItem,
    ChatRequest,
    ChatResponse,
    ChatSessionResponse,
    ChatSessionSummary,
)

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency
    genai = None


UNIBOT_SYSTEM_PROMPT = """You are UniBot, the AI assistant of UCAR (University of Carthage), an intelligent university management platform called UniSmart AI.

## Your role
You assist UCAR directors, presidents, and administrators in understanding, analyzing, and acting on data from all affiliated institutions.

## Your capabilities
- Answer questions about KPIs across any institution or group of institutions.
- Compare institutions and identify top or bottom performers on any indicator.
- Detect and explain anomalies or worrying trends using the provided context.
- Generate strategic recommendations and corrective action plans.
- Propose and draft emails to institution directors, but never send them without explicit confirmation.
- Summarize or search through institutional documents.

## Context you receive
Each message includes a [CONTEXT] block containing:
- Relevant KPI data retrieved from the database.
- Relevant document excerpts retrieved via semantic search.
- Recent alerts and anomaly detections.
- The current date and reporting period.

Always base your analysis on the provided context. If the context is insufficient to answer confidently, say so clearly and explain what data is missing.

## Language
Respond in the same language the user writes in. You support French, Arabic, and English.

## Tone and style
- Professional but conversational.
- Be direct and actionable. Lead with the insight, then support it with the data.
- When presenting numbers, always explain whether they are strong, weak, improving, or declining.
- For complex analyses, structure the response with short, clear sections.

## Actions you can trigger
When the user asks you to send an email or generate a report, never do it silently.
1. Present the full draft for review.
2. List the recipients explicitly.
3. Ask for explicit confirmation before triggering the action.
4. After confirmation, respond with a clear success message including what was sent, to whom, and when.

## Hard limits
- You only have access to UCAR network data. Never fabricate KPI values.
- Cross-institution visibility is authorized at UCAR Central level.
- Do not make irreversible decisions autonomously. Always confirm before sending emails, generating official reports, or modifying targets."""


class ChatbotAutomationService:
    """Gemini-backed chatbot orchestration for UCAR."""

    EMAIL_KEYWORDS = ("email", "mail", "courriel")
    REPORT_KEYWORDS = ("report", "rapport")
    SEND_KEYWORDS = ("send", "envoyer")

    def __init__(self, model_name: str = settings.GEMINI_MODEL) -> None:
        self.model_name = model_name

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def chat(self, db: Optional[Session], request: ChatRequest) -> ChatResponse:
        """Generate a UniBot response and optionally persist the turn."""

        session = None
        history: List[ChatMessage] = []
        created_at = datetime.utcnow()

        if self._db_enabled(db):
            session = self._get_or_create_session(db, request)
            history = self._get_recent_history(db, session.id)

        prompt = self._build_prompt(request.message, request.context, history)
        answer = self._generate_text(prompt)

        if self._db_enabled(db):
            saved_message = self._save_message(db, session, request, answer)
            created_at = saved_message.message_timestamp or created_at

        suggested_action = self._detect_suggested_action(request.message)
        return ChatResponse(
            session_id=session.id if session is not None else (request.session_id or uuid4()),
            answer=answer,
            model=self.model_name,
            created_at=created_at,
            used_context=self._context_has_data(request.context),
            requires_confirmation=suggested_action is not None,
            suggested_action=suggested_action,
        )

    def list_sessions(self, db: Session, user_id: str) -> List[ChatSessionSummary]:
        """Return all sessions for a user, most-recent first, with message counts."""

        if settings.SKIP_DB_STARTUP:
            raise HTTPException(status_code=503, detail="Session listing requires a database connection.")

        sessions = (
            db.query(ChatSession)
            .filter(ChatSession.user_id == user_id, ChatSession.status == "active")
            .order_by(ChatSession.started_at.desc())
            .all()
        )

        results: List[ChatSessionSummary] = []
        for s in sessions:
            count_row = (
                db.query(func.count(ChatMessage.id))
                .filter(ChatMessage.session_id == str(s.id))
                .scalar()
            )
            last_msg = (
                db.query(ChatMessage.message_timestamp)
                .filter(ChatMessage.session_id == str(s.id))
                .order_by(ChatMessage.message_timestamp.desc())
                .first()
            )
            results.append(
                ChatSessionSummary(
                    session_id=s.id,
                    session_name=s.session_name,
                    domain_context=s.domain_context,
                    status=s.status,
                    started_at=s.started_at,
                    message_count=count_row or 0,
                    last_message_at=last_msg[0] if last_msg else None,
                )
            )
        return results

    def get_session(self, db: Session, session_id: UUID) -> ChatSessionResponse:
        """Return session metadata and full conversation history."""

        if settings.SKIP_DB_STARTUP:
            raise HTTPException(status_code=503, detail="Chat session lookup requires a database connection.")

        session = db.query(ChatSession).filter(ChatSession.id == str(session_id)).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == str(session.id))
            .order_by(ChatMessage.message_timestamp.asc())
            .all()
        )

        return ChatSessionResponse(
            session_id=session.id,
            user_id=session.user_id,
            session_name=session.session_name,
            domain_context=session.domain_context,
            status=session.status,
            started_at=session.started_at,
            history=[
                ChatHistoryItem(
                    user_message=item.user_message,
                    bot_response=item.bot_response,
                    message_timestamp=item.message_timestamp,
                    domain_context=item.domain_context,
                )
                for item in messages
            ],
        )

    def end_session(self, db: Session, session_id: UUID) -> None:
        """Soft-delete a session by marking it ended."""

        if settings.SKIP_DB_STARTUP:
            raise HTTPException(status_code=503, detail="Requires a database connection.")

        session = db.query(ChatSession).filter(ChatSession.id == str(session_id)).first()
        if not session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        session.status = "ended"
        session.ended_at = datetime.utcnow()
        db.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _get_or_create_session(self, db: Session, request: ChatRequest) -> ChatSession:
        if request.session_id:
            session = db.query(ChatSession).filter(ChatSession.id == str(request.session_id)).first()
            if session:
                return session
            raise HTTPException(status_code=404, detail="Chat session not found")

        session = ChatSession(
            user_id=request.user_id,
            session_name=request.session_name,
            domain_context=request.domain_context,
        )
        if session.id is None:
            session.id = str(uuid4())
        db.add(session)
        db.flush()
        return session

    def _get_recent_history(self, db: Session, session_id: UUID, limit: int = 8) -> List[ChatMessage]:
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == str(session_id))
            .order_by(ChatMessage.message_timestamp.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(messages))

    def _save_message(
        self,
        db: Session,
        session: ChatSession,
        request: ChatRequest,
        answer: str,
    ) -> ChatMessage:
        # Auto-name the session from the first message if not yet named
        if not session.session_name:
            session.session_name = request.message[:80].strip()
            db.add(session)

        message = ChatMessage(
            session_id=str(session.id),
            user_message=request.message,
            bot_response=answer,
            domain_context=request.domain_context,
            confidence_score=None,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    def _build_prompt(self, message: str, context: ChatContext, history: List[ChatMessage]) -> str:
        history_lines = []
        for item in history:
            history_lines.append(f"User: {item.user_message}")
            history_lines.append(f"Assistant: {item.bot_response}")

        transcript = "\n".join(history_lines) if history_lines else "No previous conversation."

        return (
            "[SESSION HISTORY]\n"
            f"{transcript}\n"
            "[/SESSION HISTORY]\n\n"
            "[CONTEXT]\n"
            f"{self._format_context_block(context)}\n"
            "[/CONTEXT]\n\n"
            "[USER]\n"
            f"{message}\n"
            "[/USER]"
        )

    def _format_context_block(self, context: ChatContext) -> str:
        sections = [
            f"Current date: {context.current_date or datetime.utcnow().date().isoformat()}",
            f"Reporting period: {context.reporting_period or 'Not provided'}",
            "KPI data:",
            json.dumps(context.kpi_data, indent=2, ensure_ascii=False) if context.kpi_data else "[]",
            "Document excerpts:",
            "\n".join(f"- {excerpt}" for excerpt in context.document_excerpts) or "- None",
            "Recent alerts:",
            "\n".join(f"- {alert}" for alert in context.recent_alerts) or "- None",
            "Extra context:",
            json.dumps(context.extra_context, indent=2, ensure_ascii=False) if context.extra_context else "{}",
        ]
        return "\n".join(sections)

    def _generate_text(self, prompt: str) -> str:
        if not settings.GEMINI_API_KEY:
            raise HTTPException(status_code=503, detail="Gemini API is not configured. Add GEMINI_API_KEY to .env.")
        if genai is None:
            raise HTTPException(
                status_code=503,
                detail="Gemini SDK is not installed. Run: pip install google-generativeai",
            )

        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel(self.model_name)
        full_prompt = f"{UNIBOT_SYSTEM_PROMPT}\n\n{prompt}"
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.2),
        )

        if response.text:
            return response.text.strip()
        raise HTTPException(status_code=502, detail="Gemini returned an empty response.")

    @staticmethod
    def _context_has_data(context: ChatContext) -> bool:
        return any([
            bool(context.kpi_data),
            bool(context.document_excerpts),
            bool(context.recent_alerts),
            bool(context.extra_context),
            bool(context.reporting_period),
        ])

    def _detect_suggested_action(self, message: str) -> Optional[str]:
        lowered = message.lower()
        if any(w in lowered for w in self.SEND_KEYWORDS) and any(
            w in lowered for w in self.EMAIL_KEYWORDS + self.REPORT_KEYWORDS
        ):
            return "confirmation_required"
        if any(w in lowered for w in self.EMAIL_KEYWORDS):
            return "email_review"
        if any(w in lowered for w in self.REPORT_KEYWORDS):
            return "report_review"
        return None

    @staticmethod
    def _db_enabled(db: Optional[Session]) -> bool:
        return db is not None and not settings.SKIP_DB_STARTUP


chatbot_service = ChatbotAutomationService()
