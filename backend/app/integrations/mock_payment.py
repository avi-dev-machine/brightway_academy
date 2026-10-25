"""Deterministic in-memory payment provider for tests and development without Razorpay keys.

It signs and parses exactly like Razorpay, so the payment domain is exercised end to end.
It is refused in production by configuration validation.
"""

from dataclasses import replace
from uuid import uuid4

from app.exceptions import ExternalServiceError, NotFoundError
from app.integrations.payments import ProviderOrder, ProviderPayment, ProviderWebhookEvent
from app.integrations.razorpay.webhook import (
    checkout_message,
    compute_signature,
    parse_event,
    verify_signature,
)


class MockPaymentProvider:
    name = "MOCK"

    def __init__(
        self, key_secret: str = "mock_key_secret", webhook_secret: str = "mock_webhook_secret"
    ) -> None:
        self.key_secret = key_secret
        self.webhook_secret = webhook_secret
        self.orders: dict[str, ProviderOrder] = {}
        self.payments: dict[str, ProviderPayment] = {}
        self.fail_order_creation = False

    @property
    def checkout_key(self) -> str:
        return "rzp_mock_key"

    def create_order(
        self, *, amount_paise: int, currency: str, receipt: str, notes: dict[str, str]
    ) -> ProviderOrder:
        if self.fail_order_creation:
            raise ExternalServiceError("The payment provider is unavailable.")
        order = ProviderOrder(f"order_mock{uuid4().hex[:14]}", amount_paise, currency)
        self.orders[order.order_id] = order
        return order

    def verify_checkout_signature(self, *, order_id: str, payment_id: str, signature: str) -> bool:
        return verify_signature(self.key_secret, checkout_message(order_id, payment_id), signature)

    def fetch_payment(self, payment_id: str) -> ProviderPayment:
        payment = self.payments.get(payment_id)
        if payment is None:
            raise NotFoundError("Payment was not found.", code="PROVIDER_PAYMENT_NOT_FOUND")
        return payment

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        return verify_signature(self.webhook_secret, body, signature)

    def parse_webhook(self, body: bytes, event_id: str | None) -> ProviderWebhookEvent:
        return parse_event(body, event_id)

    def close(self) -> None:
        return None

    # ------------------------------------------------------------------ test helpers
    def simulate_payment(
        self,
        order_id: str,
        *,
        status: str = "captured",
        amount_paise: int | None = None,
        payment_id: str | None = None,
        method: str = "upi",
    ) -> ProviderPayment:
        order = self.orders[order_id]
        payment = ProviderPayment(
            payment_id=payment_id or f"pay_mock{uuid4().hex[:14]}",
            order_id=order_id,
            amount_paise=order.amount_paise if amount_paise is None else amount_paise,
            currency=order.currency,
            status=status,
            method=method,
        )
        self.payments[payment.payment_id] = payment
        return payment

    def set_payment_status(self, payment_id: str, status: str) -> ProviderPayment:
        payment = replace(self.payments[payment_id], status=status)
        self.payments[payment_id] = payment
        return payment

    def checkout_signature(self, order_id: str, payment_id: str) -> str:
        return compute_signature(self.key_secret, checkout_message(order_id, payment_id))

    def webhook_signature(self, body: bytes) -> str:
        return compute_signature(self.webhook_secret, body)
