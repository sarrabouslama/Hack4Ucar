"""
Database configuration and utilities
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

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
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Database:
    """Database connection manager"""

    def __init__(self, database_url: str = settings.DATABASE_URL):
        self.database_url = database_url
        self.engine = engine
        self.session_local = SessionLocal

    async def connect(self) -> None:
        """Initialize database connection"""
        # Test connection
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
                print("[OK] Database connection successful")
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            raise

    async def disconnect(self) -> None:
        """Close database connection"""
        self.engine.dispose()

    def create_tables(self) -> None:
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine)


db = Database()
