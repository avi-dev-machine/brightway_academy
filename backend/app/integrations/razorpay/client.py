"""Minimal Razorpay REST client (orders and payments) built on httpx."""

import logging
import re
from typing import Any

import httpx

from app.exceptions import ExternalServiceError, NotFoundError

logger = logging.getLogger(__name__)

_PAYMENT_ID = re.compile(r"^pay_[A-Za-z0-9]{6,40}$")


class RazorpayClient:
    def __init__(
        self,
        key_id: str,
        key_secret: str,
        *,
        base_url: str = "https://api.razorpay.com/v1",
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not key_id or not key_secret:
            raise ValueError("Razorpay requires RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET.")
        self.key_id = key_id
        self.key_secret = key_secret
        self._http = httpx.Client(
            base_url=base_url, auth=(key_id, key_secret), timeout=timeout, transport=transport
        )

    def create_order(
        self, *, amount_paise: int, currency: str, receipt: str, notes: dict[str, str]
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/orders",
            json={
                "amount": amount_paise,
                "currency": currency,
                "receipt": receipt,
                "notes": notes,
                "payment_capture": 1,
            },
        )

    def capture_payment(
        self, payment_id: str, amount_paise: int, currency: str = "INR"
    ) -> dict[str, Any]:
        if not _PAYMENT_ID.match(payment_id):
            raise NotFoundError("Payment was not found.", code="PROVIDER_PAYMENT_NOT_FOUND")
        return self._request(
            "POST",
            f"/payments/{payment_id}/capture",
            json={"amount": amount_paise, "currency": currency},
        )

    def fetch_payment(self, payment_id: str) -> dict[str, Any]:
        if not _PAYMENT_ID.match(payment_id):
            raise NotFoundError("Payment was not found.", code="PROVIDER_PAYMENT_NOT_FOUND")
        return self._request("GET", f"/payments/{payment_id}")

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            logger.error(
                "razorpay request failed", extra={"path": path, "error_type": type(exc).__name__}
            )
            raise ExternalServiceError("The payment provider is unavailable.") from exc
        if response.status_code == 200:
            data: dict[str, Any] = response.json()
            return data
        description = _error_description(response)
        logger.error(
            "razorpay request rejected",
            extra={"path": path, "status_code": response.status_code, "detail": description},
        )
        # Razorpay answers unknown ids with 400 "The id provided does not exist".
        if response.status_code == 404 or (
            response.status_code == 400 and "does not exist" in (description or "").lower()
        ):
            raise NotFoundError("Payment was not found.", code="PROVIDER_PAYMENT_NOT_FOUND")
        if response.status_code == 401:
            raise ExternalServiceError(
                "The payment provider rejected our credentials.", code="PAYMENT_PROVIDER_AUTH"
            )
        raise ExternalServiceError(
            "The payment provider rejected the request.", code="PAYMENT_PROVIDER_ERROR"
        )


def _error_description(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    error = body.get("error") if isinstance(body, dict) else None
    return error.get("description") if isinstance(error, dict) else None
