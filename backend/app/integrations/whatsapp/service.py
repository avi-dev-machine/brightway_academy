"""WhatsApp notification provider plus webhook helpers (verification and delivery statuses)."""

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any

from app.integrations.notifications import TEMPLATE_PARAMS, OutgoingMessage, SendResult
from app.integrations.whatsapp.client import WhatsAppClient
from app.models.notification import NotificationChannel


class WhatsAppProvider:
    channel = NotificationChannel.WHATSAPP
    name = "whatsapp-cloud"

    def __init__(
        self,
        client: WhatsAppClient,
        *,
        language: str = "en",
        template_names: dict[str, str] | None = None,
    ) -> None:
        self._client = client
        self._language = language
        # Internal template key -> approved Meta template name (same name by default).
        self._template_names = template_names or {}

    def send(self, message: OutgoingMessage) -> SendResult:
        param_names = TEMPLATE_PARAMS.get(message.template, [])
        message_id = self._client.send_template(
            to=message.recipient,
            template_name=self._template_names.get(message.template, message.template),
            language=self._language,
            body_params=[message.params.get(name, "") for name in param_names],
        )
        return SendResult(provider_message_id=message_id)

    def close(self) -> None:
        self._client.close()


def verify_webhook_signature(app_secret: str, body: bytes, header: str | None) -> bool:
    """Validate Meta's X-Hub-Signature-256 header ("sha256=<hex>")."""
    if not app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


@dataclass(frozen=True)
class DeliveryStatus:
    message_id: str
    status: str  # sent / delivered / read / failed
    error: str | None


def parse_status_updates(payload: dict[str, Any]) -> list[DeliveryStatus]:
    updates: list[DeliveryStatus] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            for status in (change.get("value") or {}).get("statuses") or []:
                if not isinstance(status, dict) or "id" not in status:
                    continue
                errors = status.get("errors") or []
                error = errors[0].get("title") if errors and isinstance(errors[0], dict) else None
                updates.append(DeliveryStatus(str(status["id"]), str(status.get("status")), error))
    return updates
