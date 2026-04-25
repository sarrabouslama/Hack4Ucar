"""
Database models for education research
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.models import BaseModel


class Student(BaseModel):
    """Student model"""

    __tablename__ = "students"

    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    enrollment_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), default="active", nullable=False)
    current_gpa = Column(Float, default=0.0)


class Course(BaseModel):
    """Course model"""

    __tablename__ = "courses"

    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    credits = Column(Integer, nullable=False)


class Enrollment(BaseModel):
    """Course enrollment model"""

    __tablename__ = "enrollments"

    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    enrollment_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    grade = Column(String(2), nullable=True)
    status = Column(String(50), default="active", nullable=False)


class Exam(BaseModel):
    """Exam model"""

    __tablename__ = "exams"

    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    exam_date = Column(DateTime, nullable=False)
    score = Column(Float, nullable=False)
    max_score = Column(Float, default=100.0)
    exam_type = Column(String(50), nullable=False)  # midterm, final, etc.


class ResearchIndicator(BaseModel):
    """Research indicators model"""

    __tablename__ = "research_indicators"

    metric_name = Column(String(255), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(100), nullable=True)
    reporting_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    category = Column(String(100), nullable=False)
