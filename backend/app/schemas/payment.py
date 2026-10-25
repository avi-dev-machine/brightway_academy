from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.payment import OfflineMethod, Payment
from app.models.receipt import Receipt
from app.schemas.fee import MAX_AMOUNT_PAISE

IDEMPOTENCY_KEY_PATTERN = r"^[A-Za-z0-9_-]{8,100}$"


class CreateOrderRequest(BaseModel):
    fee_id: UUID
    amount_paise: int | None = Field(
        default=None, gt=0, le=MAX_AMOUNT_PAISE, description="Defaults to the full balance."
    )


class CheckoutOrder(BaseModel):
    """Everything the frontend needs to open Razorpay Checkout."""

    payment_id: UUID
    provider: str
    provider_order_id: str
    amount_paise: int
    currency: str
    key_id: str
    fee_title: str
    student_name: str
    contact: str | None


class VerifyPaymentRequest(BaseModel):
    provider_order_id: str = Field(pattern=r"^order_[A-Za-z0-9]{6,40}$")
    provider_payment_id: str = Field(pattern=r"^pay_[A-Za-z0-9]{6,40}$")
    signature: str = Field(pattern=r"^[a-f0-9]{64}$")


class OfflinePaymentRequest(BaseModel):
    amount_paise: int = Field(gt=0, le=MAX_AMOUNT_PAISE)
    method: OfflineMethod
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    paid_on: date | None = None
    idempotency_key: str | None = Field(default=None, pattern=IDEMPOTENCY_KEY_PATTERN)


class StudentUpiPaymentRequest(BaseModel):
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    idempotency_key: str | None = Field(default=None, pattern=IDEMPOTENCY_KEY_PATTERN)


class PaymentResult(BaseModel):
    payment: Payment
    receipt: Receipt | None
    outcome: str


class PaymentConfig(BaseModel):
    provider: str
    key_id: str
    currency: str


class WebhookResult(BaseModel):
    status: str
    detail: str | None = None
