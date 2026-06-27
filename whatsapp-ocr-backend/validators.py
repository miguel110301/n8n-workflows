"""Business rules for validating OCR-extracted receipt data."""
import logging
from datetime import datetime
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ("date", "amount", "signature")

# Relative weight of each field toward the overall confidence score.
# Amount carries the most weight since it drives downstream
# reconciliation; signature is the weakest OCR signal so it counts least.
FIELD_WEIGHTS = {
    "date": 0.3,
    "amount": 0.4,
    "signature": 0.3,
}

# Business rule: anything below this confidence is escalated to a human,
# even if every required field is technically present.
VALIDATION_THRESHOLD = 0.75

_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y")


def _score_date(value: Any) -> float:
    """1.0 if `value` parses as a real date in one of the accepted formats."""
    if not isinstance(value, str) or not value.strip():
        return 0.0
    for fmt in _DATE_FORMATS:
        try:
            datetime.strptime(value.strip(), fmt)
            return 1.0
        except ValueError:
            continue
    return 0.0


def _score_amount(value: Any) -> float:
    """1.0 if `value` is a strictly positive number (receipts can't be free)."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 1.0 if amount > 0 else 0.0


def _score_signature(value: Any) -> float:
    """1.0 if a signature was detected: either a truthy flag or non-empty text."""
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, str):
        return 1.0 if value.strip() else 0.0
    return 0.0


_FIELD_SCORERS = {
    "date": _score_date,
    "amount": _score_amount,
    "signature": _score_signature,
}


def validate_receipt(data: Dict[str, Any]) -> Tuple[bool, float]:
    """Validate OCR-extracted receipt data and score it for confidence.

    Returns (is_valid, confidence_score). `is_valid` is True only when
    every required field is present and well-formed AND the weighted
    confidence clears VALIDATION_THRESHOLD -- a document with all
    fields present but low per-field quality must still be escalated.
    """
    missing = [field for field in REQUIRED_FIELDS if field not in data]
    if missing:
        logger.info("Receipt missing required fields: %s", missing)

    weighted_score = sum(
        _FIELD_SCORERS[field](data.get(field)) * weight
        for field, weight in FIELD_WEIGHTS.items()
    )

    # Blend in Claude Vision's own extraction confidence, when supplied,
    # so a well-formed field the OCR model itself was unsure about still
    # pulls the overall score down.
    ocr_confidence = data.get("ocr_confidence")
    if isinstance(ocr_confidence, (int, float)) and 0 <= ocr_confidence <= 1:
        confidence = round((weighted_score + ocr_confidence) / 2, 4)
    else:
        confidence = round(weighted_score, 4)

    is_valid = not missing and confidence >= VALIDATION_THRESHOLD
    return is_valid, confidence
