"""Database models for documents ingestion"""

import enum
import json

from sqlalchemy import Column, Integer, String, Text, Index, Computed, JSON
from sqlalchemy.dialects.postgresql import TSVECTOR

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
    extracted_text = Column(Text, nullable=True)
    parser_name = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=True)
    module_classification = Column(String(255), nullable=True)
    institution_id = Column(String(100), nullable=True)
    

    

