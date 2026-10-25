from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class NotificationChannel(StrEnum):
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"
    EMAIL = "EMAIL"


class NotificationStatus(StrEnum):
    QUEUED = "QUEUED"
    SENDING = "SENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class NotificationTemplate(StrEnum):
    FEE_REMINDER = "fee_reminder"
    PAYMENT_SUCCESS = "payment_success"


class Notification(BaseModel):
    id: UUID
    student_id: UUID | None
    fee_id: UUID | None
    payment_id: UUID | None
    channel: NotificationChannel
    recipient: str
    template: str
    payload: dict[str, Any]
    status: NotificationStatus
    provider_message_id: str | None
    attempts: int
    max_attempts: int
    next_attempt_at: datetime
    last_error: str | None
    dedupe_key: str | None
    sent_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime
