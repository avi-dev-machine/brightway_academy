"""Provider-independent payment interface. The payment domain only depends on this module."""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderOrder:
    order_id: str
    amount_paise: int
    currency: str


@dataclass(frozen=True)
class ProviderPayment:
    payment_id: str
    order_id: str | None
    amount_paise: int
    currency: str
    # Provider-native status: created / authorized / captured / refunded / failed
    status: str
    method: str | None = None
    error_reason: str | None = None


@dataclass(frozen=True)
class ProviderRefund:
    refund_id: str
    payment_id: str
    amount_paise: int


@dataclass(frozen=True)
class ProviderWebhookEvent:
    event_id: str
    event_type: str
    payment: ProviderPayment | None
    refund: ProviderRefund | None
    order_id: str | None
    payload: dict[str, Any] = field(repr=False)


class PaymentProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def checkout_key(self) -> str: ...

    def create_order(
        self, *, amount_paise: int, currency: str, receipt: str, notes: dict[str, str]
    ) -> ProviderOrder: ...

    def verify_checkout_signature(
        self, *, order_id: str, payment_id: str, signature: str
    ) -> bool: ...

    def fetch_payment(self, payment_id: str) -> ProviderPayment: ...

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool: ...

    def parse_webhook(self, body: bytes, event_id: str | None) -> ProviderWebhookEvent: ...

    def close(self) -> None: ...
