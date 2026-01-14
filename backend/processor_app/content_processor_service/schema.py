from enum import Enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SubmissionStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PASSED = "PASSED"
    FAILED = "FAILED"


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True, index=True)
    content = Column(String, nullable=False)
    status = Column(SQLEnum(SubmissionStatus), default=SubmissionStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processing_started_at = Column(DateTime, nullable=True)  # Track when PROCESSING started
    processed_at = Column(DateTime, nullable=True)  # When finally PASSED/FAILED
