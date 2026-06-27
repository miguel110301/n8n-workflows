"""FastAPI backend for the WhatsApp OCR pipeline.

Sits between n8n (orchestration + WhatsApp/Claude Vision integration)
and PostgreSQL. n8n forwards OCR-extracted receipt data here; this
service validates it, persists it, and routes low-confidence documents
to a human review queue.
"""
import logging
from datetime import datetime
from typing import Any, Dict, Literal, Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import settings
from database import Base, engine, get_db
from models import AuditLog, DocumentRecord
from validators import validate_receipt

logger = logging.getLogger(__name__)

settings.validate()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WhatsApp OCR Pipeline Backend",
    description="Validates OCR receipt data and manages the human review queue.",
    version="1.0.0",
)


# ---------- Request / response schemas ----------

class ProcessDocumentRequest(BaseModel):
    phone_number: str = Field(..., min_length=1, description="WhatsApp sender, e.g. '15551234567'")
    extracted_data: Dict[str, Any] = Field(
        ..., description="Structured fields produced by Claude Vision OCR (date, amount, signature, ...)"
    )
    media_url: Optional[str] = Field(None, description="Source image/media reference, kept for audit purposes")


class ProcessDocumentResponse(BaseModel):
    document_id: int
    phone_number: str
    status: str
    confidence: float


class StatusResponse(BaseModel):
    document_id: int
    phone_number: str
    status: str
    confidence: float
    timestamp: datetime


class EscalateRequest(BaseModel):
    document_id: int
    reviewer: str = Field(..., min_length=1, description="Identifier of the human making the decision")
    decision: Literal["approved", "rejected"]
    notes: Optional[str] = Field(None, max_length=500)


class EscalateResponse(BaseModel):
    document_id: int
    status: str
    reviewer: str
    decision: str


# ---------- Endpoints ----------

@app.post("/api/process-document/", response_model=ProcessDocumentResponse)
def process_document(
    payload: ProcessDocumentRequest, db: Session = Depends(get_db)
) -> ProcessDocumentResponse:
    """Validate OCR-extracted receipt data and persist the result.

    Business rule: documents that fail validation or fall below the
    confidence threshold are marked "escalated" rather than rejected
    outright, so a human can make the final call via /api/escalate/.
    """
    try:
        is_valid, confidence = validate_receipt(payload.extracted_data)
    except Exception:
        logger.exception("Validation failed for phone=%s", payload.phone_number)
        raise HTTPException(status_code=400, detail="Could not validate extracted_data")

    status = "validated" if is_valid else "escalated"

    record = DocumentRecord(
        phone=payload.phone_number,
        extracted_data=payload.extracted_data,
        status=status,
        confidence=confidence,
    )

    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        logger.exception("Failed to persist document for phone=%s", payload.phone_number)
        raise HTTPException(status_code=500, detail="Could not save document record")

    logger.info(
        "Processed document id=%s phone=%s status=%s confidence=%.2f",
        record.id, record.phone, record.status, record.confidence,
    )

    return ProcessDocumentResponse(
        document_id=record.id,
        phone_number=record.phone,
        status=record.status,
        confidence=record.confidence,
    )


@app.get("/api/status/{phone_number}", response_model=StatusResponse)
def get_status(phone_number: str, db: Session = Depends(get_db)) -> StatusResponse:
    """Return the most recent document's processing status for a phone number."""
    record = (
        db.query(DocumentRecord)
        .filter(DocumentRecord.phone == phone_number)
        .order_by(DocumentRecord.timestamp.desc())
        .first()
    )
    if record is None:
        raise HTTPException(status_code=404, detail=f"No documents found for {phone_number}")

    return StatusResponse(
        document_id=record.id,
        phone_number=record.phone,
        status=record.status,
        confidence=record.confidence,
        timestamp=record.timestamp,
    )


@app.post("/api/escalate/", response_model=EscalateResponse)
def escalate(payload: EscalateRequest, db: Session = Depends(get_db)) -> EscalateResponse:
    """Record a human reviewer's decision on an escalated document.

    This is the exit point of the human review queue: it writes the
    audit trail (who decided, when, what) and moves the document out
    of "escalated" into a terminal "validated"/"rejected" state.
    """
    record = db.query(DocumentRecord).filter(DocumentRecord.id == payload.document_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail=f"Document {payload.document_id} not found")

    record.status = "validated" if payload.decision == "approved" else "rejected"
    audit_entry = AuditLog(
        document_id=record.id,
        reviewer=payload.reviewer,
        decision=payload.decision,
        notes=payload.notes,
    )

    try:
        db.add(audit_entry)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to record audit log for document_id=%s", payload.document_id)
        raise HTTPException(status_code=500, detail="Could not record review decision")

    logger.info(
        "Document id=%s reviewed by=%s decision=%s",
        record.id, payload.reviewer, payload.decision,
    )

    return EscalateResponse(
        document_id=record.id,
        status=record.status,
        reviewer=payload.reviewer,
        decision=payload.decision,
    )
