"""Razorpay adapter implementing the PaymentProvider interface."""

from app.exceptions import ServiceNotConfiguredError
from app.integrations.payments import ProviderOrder, ProviderPayment, ProviderWebhookEvent
from app.integrations.razorpay.client import RazorpayClient
from app.integrations.razorpay.webhook import (
    checkout_message,
    parse_event,
    payment_from_entity,
    verify_signature,
)


class RazorpayPaymentProvider:
    name = "RAZORPAY"

    def __init__(self, client: RazorpayClient, webhook_secret: str) -> None:
        self._client = client
        self._webhook_secret = webhook_secret

    @property
    def checkout_key(self) -> str:
        return self._client.key_id

    def create_order(
        self, *, amount_paise: int, currency: str, receipt: str, notes: dict[str, str]
    ) -> ProviderOrder:
        data = self._client.create_order(
            amount_paise=amount_paise, currency=currency, receipt=receipt, notes=notes
        )
        return ProviderOrder(
            order_id=str(data["id"]),
            amount_paise=int(data["amount"]),
            currency=str(data["currency"]),
        )

    def verify_checkout_signature(self, *, order_id: str, payment_id: str, signature: str) -> bool:
        return verify_signature(
            self._client.key_secret, checkout_message(order_id, payment_id), signature
        )

    def fetch_payment(self, payment_id: str) -> ProviderPayment:
        data = self._client.fetch_payment(payment_id)
        if data.get("status") == "authorized":
            try:
                data = self._client.capture_payment(
                    payment_id, int(data["amount"]), str(data.get("currency") or "INR")
                )
            except Exception:
                pass
        return payment_from_entity(data)

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        if not self._webhook_secret:
            raise ServiceNotConfiguredError(
                "Razorpay webhooks are not configured (missing secret)."
            )
        return verify_signature(self._webhook_secret, body, signature)

    def parse_webhook(self, body: bytes, event_id: str | None) -> ProviderWebhookEvent:
        return parse_event(body, event_id)

    def close(self) -> None:
        self._client.close()
