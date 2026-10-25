"""WhatsApp template messages through Fast2SMS (WHATSAPP_PROVIDER=fast2sms).

API: GET https://www.fast2sms.com/dev/whatsapp with the API key in the `authorization`
header and query parameters message_id (approved template id), phone_number_id (the
WhatsApp Business number id from the Fast2SMS panel), numbers (10-digit Indian mobile)
and variables_values (template variables separated by "|").
"""

import logging
from typing import Any

import httpx

from app.exceptions import ExternalServiceError
from app.integrations.notifications import (
    TEMPLATE_PARAMS,
    OutgoingMessage,
    PermanentDeliveryError,
    SendResult,
)
from app.integrations.sms.client import ipv4_transport
from app.models.notification import NotificationChannel

logger = logging.getLogger(__name__)

FAST2SMS_WHATSAPP_URL = "https://www.fast2sms.com/dev/whatsapp"


class Fast2SmsWhatsAppProvider:
    channel = NotificationChannel.WHATSAPP
    name = "fast2sms-whatsapp"

    def __init__(
        self,
        api_key: str,
        phone_number_id: str,
        template_ids: dict[str, str],
        *,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key or not phone_number_id:
            raise ValueError("Fast2SMS WhatsApp requires an API key and a phone_number_id.")
        self._phone_number_id = phone_number_id
        self._template_ids = template_ids
        self._http = httpx.Client(
            headers={"authorization": api_key},
            timeout=timeout,
            transport=transport or ipv4_transport(),
        )

    def send(self, message: OutgoingMessage) -> SendResult:
        template_id = self._template_ids.get(message.template)
        if not template_id:
            raise PermanentDeliveryError(
                f"No Fast2SMS WhatsApp template id is configured for '{message.template}'."
            )
        if not message.recipient.startswith("+91") or len(message.recipient) != 13:
            raise PermanentDeliveryError("WhatsApp via Fast2SMS supports Indian numbers only.")
        # "|" separates variables, so it must not appear inside a value.
        values = [
            message.params.get(name, "").replace("|", "/")
            for name in TEMPLATE_PARAMS.get(message.template, [])
        ]
        params = {
            "message_id": template_id,
            "phone_number_id": self._phone_number_id,
            "numbers": message.recipient[3:],
            "variables_values": "|".join(values),
        }
        try:
            response = self._http.get(FAST2SMS_WHATSAPP_URL, params=params)
        except httpx.HTTPError as exc:
            raise ExternalServiceError("The WhatsApp provider is unavailable.") from exc
        body = _json(response)
        if response.status_code == 200 and (
            body.get("status") is True or body.get("return") is True
        ):
            return SendResult(provider_message_id=str(body.get("request_id") or "") or None)
        logger.error(
            "fast2sms whatsapp send rejected",
            extra={
                "status_code": response.status_code,
                "provider_status": body.get("status_code"),
                "detail": body.get("message"),
            },
        )
        # Server errors, throttling and account/auth problems (e.g. IP not whitelisted) can be
        # fixed without changing the message, so they are retried with backoff.
        if response.status_code >= 500 or response.status_code in (401, 403, 429):
            raise ExternalServiceError("The WhatsApp provider rejected the request.")
        raise PermanentDeliveryError(f"WhatsApp message rejected: {body.get('message', '')}")

    def close(self) -> None:
        self._http.close()


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    return body if isinstance(body, dict) else {}
