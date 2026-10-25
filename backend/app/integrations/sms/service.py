"""SMS notification provider."""

from app.integrations.notifications import OutgoingMessage, PermanentDeliveryError, SendResult
from app.integrations.sms.client import Fast2SmsClient
from app.models.notification import NotificationChannel


class SmsProvider:
    channel = NotificationChannel.SMS
    name = "fast2sms"

    def __init__(self, client: Fast2SmsClient) -> None:
        self._client = client

    def send(self, message: OutgoingMessage) -> SendResult:
        if not message.recipient.startswith("+91") or len(message.recipient) != 13:
            raise PermanentDeliveryError("SMS can only be sent to Indian mobile numbers.")
        request_id = self._client.send(number=message.recipient[3:], message=message.text)
        return SendResult(provider_message_id=request_id or None)

    def close(self) -> None:
        self._client.close()
