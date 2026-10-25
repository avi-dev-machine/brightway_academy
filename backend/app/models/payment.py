"""Payment domain: records and the payment state machine (independent of any provider)."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel

from app.exceptions import InvalidStateError


class PaymentStatus(StrEnum):
    CREATED = "CREATED"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class PaymentProviderName(StrEnum):
    RAZORPAY = "RAZORPAY"
    MOCK = "MOCK"
    OFFLINE = "OFFLINE"


class OfflineMethod(StrEnum):
    CASH = "CASH"
    UPI = "UPI"
    BANK_TRANSFER = "BANK_TRANSFER"
    CHEQUE = "CHEQUE"
    CARD = "CARD"
    OTHER = "OTHER"


# A failed online attempt can still succeed later: Razorpay allows retries on the same order.
ALLOWED_TRANSITIONS: dict[PaymentStatus, frozenset[PaymentStatus]] = {
    PaymentStatus.CREATED: frozenset(
        {PaymentStatus.PENDING, PaymentStatus.SUCCESS, PaymentStatus.FAILED}
    ),
    PaymentStatus.PENDING: frozenset({PaymentStatus.SUCCESS, PaymentStatus.FAILED}),
    PaymentStatus.FAILED: frozenset({PaymentStatus.PENDING, PaymentStatus.SUCCESS}),
    PaymentStatus.SUCCESS: frozenset({PaymentStatus.REFUNDED}),
    PaymentStatus.REFUNDED: frozenset(),
}


def can_transition(current: PaymentStatus, target: PaymentStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def ensure_transition(current: PaymentStatus, target: PaymentStatus) -> None:
    if not can_transition(current, target):
        raise InvalidStateError(
            f"Payment cannot move from {current} to {target}.", code="INVALID_PAYMENT_TRANSITION"
        )


class Payment(BaseModel):
    id: UUID
    fee_id: UUID
    student_id: UUID
    amount_paise: int
    currency: str
    provider: PaymentProviderName
    method: str | None
    status: PaymentStatus
    provider_order_id: str | None
    provider_payment_id: str | None
    reference: str | None
    notes: str | None
    failure_reason: str | None
    requires_review: bool
    review_reason: str | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime
