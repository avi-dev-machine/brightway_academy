"""Provider-independent notification interface, message templates and a development provider."""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from app.exceptions import ExternalServiceError
from app.models.notification import NotificationChannel, NotificationTemplate

logger = logging.getLogger(__name__)

TEMPLATE_TEXT: dict[str, str] = {
    NotificationTemplate.FEE_REMINDER: (
        "Dear {name}, your fee '{fee_title}' of {amount} is due on {due_date}. "
        "Please pay at the earliest. - {academy_name}"
    ),
    NotificationTemplate.PAYMENT_SUCCESS: (
        "Dear {name}, we have received {amount} towards '{fee_title}'. "
        "Receipt no. {receipt_number}. Thank you! - {academy_name}"
    ),
}

# Order of body parameters for WhatsApp templates; the approved Meta templates must match.
TEMPLATE_PARAMS: dict[str, list[str]] = {
    NotificationTemplate.FEE_REMINDER: ["name", "fee_title", "amount", "due_date"],
    NotificationTemplate.PAYMENT_SUCCESS: ["name", "amount", "fee_title", "receipt_number"],
}


def render_text(template: str, params: dict[str, str]) -> str:
    return TEMPLATE_TEXT[template].format_map(defaultdict(str, params))


def mask_recipient(recipient: str) -> str:
    return "*" * max(len(recipient) - 4, 0) + recipient[-4:]


class PermanentDeliveryError(ExternalServiceError):
    """The provider rejected the message for a reason a retry cannot fix."""

    code = "PERMANENT_DELIVERY_FAILURE"


@dataclass(frozen=True)
class OutgoingMessage:
    recipient: str  # E.164, e.g. +919812345678
    template: str
    params: dict[str, str]
    text: str


@dataclass(frozen=True)
class SendResult:
    provider_message_id: str | None


class NotificationProvider(Protocol):
    @property
    def channel(self) -> NotificationChannel: ...

    @property
    def name(self) -> str: ...

    def send(self, message: OutgoingMessage) -> SendResult: ...

    def close(self) -> None: ...


@dataclass
class LoggingNotificationProvider:
    """Development-only provider: records and logs messages instead of sending them."""

    channel: NotificationChannel
    sent: list[OutgoingMessage] = field(default_factory=list)
    fail_with: Exception | None = None

    @property
    def name(self) -> str:
        return f"log-{self.channel.lower()}"

    def send(self, message: OutgoingMessage) -> SendResult:
        if self.fail_with is not None:
            raise self.fail_with
        self.sent.append(message)
        logger.info(
            "notification logged (development provider, not sent)",
            extra={
                "channel": self.channel,
                "template": message.template,
                "recipient": mask_recipient(message.recipient),
            },
        )
        return SendResult(provider_message_id=f"log-{uuid4().hex}")

    def close(self) -> None:
        return None
