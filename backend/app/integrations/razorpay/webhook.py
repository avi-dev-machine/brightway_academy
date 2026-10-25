"""Razorpay signature verification and webhook parsing."""

import hashlib
import hmac
import json
from typing import Any

from app.exceptions import PaymentVerificationError
from app.integrations.payments import ProviderPayment, ProviderRefund, ProviderWebhookEvent


def compute_signature(secret: str, message: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_signature(secret: str, message: bytes, signature: str | None) -> bool:
    if not secret or not signature:
        return False
    return hmac.compare_digest(compute_signature(secret, message), signature)


def checkout_message(order_id: str, payment_id: str) -> bytes:
    """Message signed by Razorpay Checkout: "<order_id>|<payment_id>"."""
    return f"{order_id}|{payment_id}".encode()


def payment_from_entity(entity: dict[str, Any]) -> ProviderPayment:
    return ProviderPayment(
        payment_id=str(entity["id"]),
        order_id=entity.get("order_id"),
        amount_paise=int(entity["amount"]),
        currency=str(entity.get("currency") or "INR"),
        status=str(entity.get("status") or ""),
        method=entity.get("method"),
        error_reason=entity.get("error_description") or entity.get("error_reason"),
    )


def _malformed() -> PaymentVerificationError:
    return PaymentVerificationError("Malformed webhook payload.", code="INVALID_WEBHOOK_PAYLOAD")


def parse_event(body: bytes, event_id: str | None) -> ProviderWebhookEvent:
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _malformed() from exc
    if not isinstance(data, dict) or not isinstance(data.get("event"), str):
        raise _malformed()
    raw_payload = data.get("payload")
    payload: dict[str, Any] = raw_payload if isinstance(raw_payload, dict) else {}

    def entity(name: str) -> dict[str, Any] | None:
        part = payload.get(name)
        value = part.get("entity") if isinstance(part, dict) else None
        return value if isinstance(value, dict) else None

    try:
        payment_entity = entity("payment")
        payment = payment_from_entity(payment_entity) if payment_entity else None
        refund_entity = entity("refund")
        refund = (
            ProviderRefund(
                refund_id=str(refund_entity["id"]),
                payment_id=str(refund_entity["payment_id"]),
                amount_paise=int(refund_entity["amount"]),
            )
            if refund_entity
            else None
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _malformed() from exc

    order_entity = entity("order")
    order_id = (payment.order_id if payment else None) or (
        str(order_entity["id"]) if order_entity and "id" in order_entity else None
    )
    return ProviderWebhookEvent(
        # Razorpay sends a unique x-razorpay-event-id header; fall back to the body hash.
        event_id=event_id or hashlib.sha256(body).hexdigest(),
        event_type=data["event"],
        payment=payment,
        refund=refund,
        order_id=order_id,
        payload=data,
    )
