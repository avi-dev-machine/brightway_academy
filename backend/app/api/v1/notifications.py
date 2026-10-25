import hmac
import json
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse
from starlette.concurrency import run_in_threadpool

from app.dependencies import AdminUser, ContainerDep, notification_service
from app.exceptions import (
    ForbiddenError,
    PaymentVerificationError,
    ServiceNotConfiguredError,
    ValidationFailedError,
)
from app.integrations.whatsapp.service import parse_status_updates, verify_webhook_signature
from app.models.notification import Notification, NotificationChannel, NotificationStatus
from app.schemas.common import ApiResponse, MessageOut, ok
from app.utils.pagination import PageDep, paged
from app.utils.rate_limit import client_ip

router = APIRouter()

MAX_WEBHOOK_BYTES = 512 * 1024


@router.get("", response_model=ApiResponse[list[Notification]])
def list_notifications(
    user: AdminUser,
    container: ContainerDep,
    params: PageDep,
    status: NotificationStatus | None = None,
    channel: NotificationChannel | None = None,
    student_id: UUID | None = None,
) -> ApiResponse[list[Notification]]:
    return paged(
        notification_service(container).search(
            status=status, channel=channel, student_id=student_id, params=params
        )
    )


@router.post("/{notification_id}/retry", response_model=ApiResponse[Notification])
def retry_notification(
    notification_id: UUID, user: AdminUser, container: ContainerDep
) -> ApiResponse[Notification]:
    return ok(notification_service(container).retry(user, notification_id))


@router.get("/webhooks/whatsapp", response_class=PlainTextResponse)
def verify_whatsapp_webhook(
    container: ContainerDep,
    hub_mode: Annotated[str | None, Query(alias="hub.mode")] = None,
    hub_verify_token: Annotated[str | None, Query(alias="hub.verify_token")] = None,
    hub_challenge: Annotated[str | None, Query(alias="hub.challenge", max_length=200)] = None,
) -> PlainTextResponse:
    """Meta's one-time subscription handshake."""
    expected = container.settings.whatsapp_webhook_verify_token.get_secret_value()
    if not expected:
        raise ServiceNotConfiguredError("WhatsApp webhooks are not configured.")
    if (
        hub_mode != "subscribe"
        or not hub_verify_token
        or not hmac.compare_digest(hub_verify_token, expected)
    ):
        raise ForbiddenError("Webhook verification failed.")
    return PlainTextResponse(hub_challenge or "")


@router.post("/webhooks/whatsapp", response_model=ApiResponse[MessageOut])
async def whatsapp_status_webhook(
    request: Request, container: ContainerDep
) -> ApiResponse[MessageOut]:
    """Delivery status callbacks. Trust comes only from the X-Hub-Signature-256 header."""
    container.webhook_limiter.hit(f"whatsapp:{client_ip(request)}")
    app_secret = container.settings.whatsapp_app_secret.get_secret_value()
    if not app_secret:
        raise ServiceNotConfiguredError("WhatsApp webhooks are not configured.")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_WEBHOOK_BYTES:
            raise ValidationFailedError("Webhook payload is too large.", code="PAYLOAD_TOO_LARGE")
    if not verify_webhook_signature(
        app_secret, bytes(body), request.headers.get("x-hub-signature-256")
    ):
        raise PaymentVerificationError(
            "Invalid webhook signature.", code="INVALID_WEBHOOK_SIGNATURE"
        )
    try:
        payload = json.loads(bytes(body))
    except ValueError as exc:
        raise ValidationFailedError("Malformed webhook payload.") from exc
    statuses = parse_status_updates(payload if isinstance(payload, dict) else {})
    updated = await run_in_threadpool(
        notification_service(container).apply_delivery_statuses,
        NotificationChannel.WHATSAPP,
        statuses,
    )
    return ok(MessageOut(message=f"{updated} notification(s) updated."))
