"""
Database models for documents ingestion
"""

from sqlalchemy import Column, String, Integer, Text, Enum
import enum

from app.core.models import BaseModel


class DocumentStatus(str, enum.Enum):
    """Document status enum"""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class Document(BaseModel):
    """Document model"""

    __tablename__ = "documents"

    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)
    status = Column(String(50), default=DocumentStatus.PENDING, nullable=False)
    extracted_data = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=True)
