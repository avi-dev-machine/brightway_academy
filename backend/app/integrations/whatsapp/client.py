"""WhatsApp Cloud API (Meta Graph API) client for template messages."""

import logging
from typing import Any

import httpx

from app.exceptions import ExternalServiceError
from app.integrations.notifications import PermanentDeliveryError

logger = logging.getLogger(__name__)

# Graph API error codes that will not succeed on retry (invalid recipient / template / params).
_PERMANENT_ERROR_CODES = {
    100,
    131008,
    131009,
    131021,
    131026,
    131051,
    132000,
    132001,
    132005,
    132012,
}


class WhatsAppClient:
    def __init__(
        self,
        access_token: str,
        phone_number_id: str,
        *,
        api_version: str = "v21.0",
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not access_token or not phone_number_id:
            raise ValueError(
                "WhatsApp requires WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID."
            )
        self._phone_number_id = phone_number_id
        self._http = httpx.Client(
            base_url=f"https://graph.facebook.com/{api_version}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=timeout,
            transport=transport,
        )

    def send_template(
        self, *, to: str, template_name: str, language: str, body_params: list[str]
    ) -> str:
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to.lstrip("+"),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": value} for value in body_params],
                    }
                ],
            },
        }
        try:
            response = self._http.post(f"/{self._phone_number_id}/messages", json=payload)
        except httpx.HTTPError as exc:
            raise ExternalServiceError("WhatsApp is unavailable.") from exc
        if response.status_code == 200:
            return str(response.json()["messages"][0]["id"])
        error = _error(response)
        logger.error(
            "whatsapp send rejected",
            extra={"status_code": response.status_code, "provider_error_code": error.get("code")},
        )
        if response.status_code == 400 and error.get("code") in _PERMANENT_ERROR_CODES:
            raise PermanentDeliveryError(
                f"WhatsApp rejected the message: {error.get('message', '')}"
            )
        raise ExternalServiceError("WhatsApp rejected the request.")

    def close(self) -> None:
        self._http.close()


def _error(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}
    error = body.get("error") if isinstance(body, dict) else None
    return error if isinstance(error, dict) else {}
