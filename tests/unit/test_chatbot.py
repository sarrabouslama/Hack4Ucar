"""Unit tests for chatbot automation service helpers."""

from uuid import UUID

from app.modules.chatbot_automation.models import ChatContext, ChatRequest
from app.modules.chatbot_automation.services import ChatbotAutomationService


class DummySession:
    """Very small session stub for chatbot tests."""

    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        return None

    def commit(self):
        self.committed = True

    def refresh(self, _obj):
        return None


def test_format_context_block_includes_all_sections():
    service = ChatbotAutomationService(model_name="test-model")
    context = ChatContext(
        kpi_data=[{"institution": "ENIT", "graduation_rate": 91.2}],
        document_excerpts=["Audit report excerpt"],
        recent_alerts=["Drop in research output"],
        reporting_period="2026-Q1",
        current_date="2026-04-26",
        extra_context={"scope": "UCAR central"},
    )

    rendered = service._format_context_block(context)

    assert "Current date: 2026-04-26" in rendered
    assert '"institution": "ENIT"' in rendered
    assert "- Audit report excerpt" in rendered
    assert "- Drop in research output" in rendered
    assert '"scope": "UCAR central"' in rendered


def test_chat_creates_preview_response_without_database(monkeypatch):
    service = ChatbotAutomationService(model_name="test-model")
    request = ChatRequest(message="Compare the top institutions this quarter.")

    monkeypatch.setattr(service, "_generate_text", lambda _prompt: "Here is the comparison.")

    response = service.chat(None, request)

    assert response.answer == "Here is the comparison."
    assert response.model == "test-model"
    assert isinstance(response.session_id, UUID)
    assert response.used_context is False


def test_chat_persists_session_and_message(monkeypatch):
    service = ChatbotAutomationService(model_name="test-model")
    db = DummySession()
    request = ChatRequest(
        message="Draft an email to the directors.",
        user_id="central-admin",
        session_name="Executive review",
        domain_context="governance",
        context=ChatContext(reporting_period="2026-Q1"),
    )

    monkeypatch.setattr(service, "_generate_text", lambda _prompt: "Draft ready for review.")
    monkeypatch.setattr(service, "_db_enabled", lambda _db: True)
    monkeypatch.setattr(service, "_get_recent_history", lambda _db, _session_id: [])

    response = service.chat(db, request)

    assert db.committed is True
    assert len(db.added) == 2
    assert response.requires_confirmation is True
    assert response.suggested_action == "email_review"
