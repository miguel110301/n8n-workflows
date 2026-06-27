"""SQLAlchemy ORM models for the WhatsApp OCR pipeline."""
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class DocumentRecord(Base):
    """A single receipt processed from a WhatsApp message.

    `status` tracks where the document sits in the pipeline:
    pending -> validated | escalated -> validated | rejected
    (the last transition happens once a human resolves an escalation
    via POST /api/escalate/).
    """

    __tablename__ = "document_records"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(32), nullable=False, index=True)
    extracted_data = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    confidence = Column(Float, nullable=False, default=0.0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    audit_logs = relationship(
        "AuditLog", back_populates="document", cascade="all, delete-orphan"
    )


class AuditLog(Base):
    """Audit trail of every human decision made on an escalated document."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("document_records.id"), nullable=False, index=True
    )
    reviewer = Column(String(100), nullable=False)
    decision = Column(String(20), nullable=False)  # "approved" | "rejected"
    notes = Column(String(500), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship("DocumentRecord", back_populates="audit_logs")
