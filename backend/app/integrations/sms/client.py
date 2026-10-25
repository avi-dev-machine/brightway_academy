"""Fast2SMS client (Quick SMS route). Used when SMS_PROVIDER=fast2sms."""

import logging
from typing import Any

import httpx

from app.exceptions import ExternalServiceError
from app.integrations.notifications import PermanentDeliveryError

logger = logging.getLogger(__name__)

FAST2SMS_URL = "https://www.fast2sms.com/dev/bulkV2"
FAST2SMS_WALLET_URL = "https://www.fast2sms.com/dev/wallet"


def ipv4_transport() -> httpx.HTTPTransport:
    """Fast2SMS only accepts API calls from allow-listed IPs. Hosts with IPv6 would
    otherwise connect over IPv6, whose addresses rotate, so pin connections to IPv4."""
    # Source address for outgoing connections (selects IPv4); this is not a listening socket.
    return httpx.HTTPTransport(local_address="0.0.0.0")  # noqa: S104


class Fast2SmsClient:
    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("SMS requires SMS_PROVIDER_API_KEY.")
        self._http = httpx.Client(
            headers={"authorization": api_key},
            timeout=timeout,
            transport=transport or ipv4_transport(),
        )

    def wallet_balance(self) -> str:
        """Remaining Fast2SMS wallet balance (INR). Read-only; useful to verify the key/IP."""
        try:
            response = self._http.get(FAST2SMS_WALLET_URL)
        except httpx.HTTPError as exc:
            raise ExternalServiceError("The SMS provider is unavailable.") from exc
        body = _json(response)
        if response.status_code == 200 and body.get("return") is True:
            return str(body.get("wallet", ""))
        logger.error(
            "fast2sms wallet check rejected",
            extra={"status_code": response.status_code, "detail": body.get("message")},
        )
        raise ExternalServiceError(f"Fast2SMS refused the request: {body.get('message', '')}")

    def send(self, *, number: str, message: str) -> str:
        """Send to a 10-digit Indian mobile number. Returns the provider request id."""
        payload: dict[str, Any] = {
            "route": "q",
            "message": message,
            "language": "english",
            "flash": 0,
            "numbers": number,
        }
        try:
            response = self._http.post(FAST2SMS_URL, json=payload)
        except httpx.HTTPError as exc:
            raise ExternalServiceError("The SMS provider is unavailable.") from exc
        body = _json(response)
        if response.status_code == 200 and body.get("return") is True:
            return str(body.get("request_id", ""))
        logger.error(
            "sms send rejected",
            extra={"status_code": response.status_code, "provider_status": body.get("status_code")},
        )
        if response.status_code in (400, 412):
            raise PermanentDeliveryError("The SMS provider rejected the message.")
        raise ExternalServiceError("The SMS provider rejected the request.")

    def close(self) -> None:
        self._http.close()


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}
