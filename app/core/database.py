"""Database configuration and utilities."""

from importlib import import_module
from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Database:
    """Database connection manager."""

    def __init__(self, database_url: str = settings.DATABASE_URL):
        self.database_url = database_url
        self.engine = engine
        self.session_local = SessionLocal

    async def connect(self) -> None:
        """Initialize database connection."""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                print("Database connection successful")
        except Exception as exc:
            print(f"Database connection failed: {exc}")
            raise

    async def disconnect(self) -> None:
        """Close database connection."""
        self.engine.dispose()

    def create_tables(self) -> None:
        """Create all tables."""
        self._import_model_modules()
        Base.metadata.create_all(bind=self.engine)

    def create_documents_table(self) -> None:
        """Create only the documents table for the OCR pipeline."""

        import_module("app.modules.documents_ingestion.db_models")
        from app.modules.documents_ingestion.db_models import Document

        Document.__table__.create(bind=self.engine, checkfirst=True)
        self._ensure_documents_schema()

    def _ensure_documents_schema(self) -> None:
        """Apply lightweight schema updates for existing documents table."""

        inspector = inspect(self.engine)
        if "documents" not in inspector.get_table_names():
            return

        existing_columns = {col["name"] for col in inspector.get_columns("documents")}

        # Added for document-to-module classification.
        if "module_classification" not in existing_columns:
            with self.engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE documents "
                        "ADD COLUMN module_classification VARCHAR(100)"
                    )
                )

    def create_chatbot_tables(self) -> None:
        """Create chatbot tables needed for conversation history."""

        import_module("app.modules.chatbot_automation.db_models")
        from app.modules.chatbot_automation.db_models import ChatMessage, ChatSession

        ChatSession.__table__.create(bind=self.engine, checkfirst=True)
        ChatMessage.__table__.create(bind=self.engine, checkfirst=True)

    @staticmethod
    def _import_model_modules() -> None:
        """Import all model modules so SQLAlchemy metadata is populated."""

        modules = [
            "app.modules.documents_ingestion.db_models",
            "app.modules.education_research.db_models",
            "app.modules.finance_partnerships_hr.db_models",
            "app.modules.environment_infrastructure.db_models",
            "app.modules.chatbot_automation.db_models",
        ]
        for module_path in modules:
            import_module(module_path)


db = Database()
