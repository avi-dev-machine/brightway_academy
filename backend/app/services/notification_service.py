"""Notification queue: enqueue (deduplicated), deliver with retries, track delivery status."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from app.core.permissions import CurrentUser
from app.db.client import Database, DbConnection
from app.exceptions import AppError, InvalidStateError, NotFoundError
from app.integrations.notifications import (
    NotificationProvider,
    OutgoingMessage,
    PermanentDeliveryError,
    render_text,
)
from app.integrations.whatsapp.service import DeliveryStatus
from app.models.fee import FeeStatus
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationTemplate,
)
from app.models.settings import NotificationSettings, SettingKey
from app.repositories.base import Row
from app.repositories.fee_repository import FeeRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.notification import ProcessResult
from app.services.audit_service import record_audit
from app.services.settings_service import load_academy, load_setting
from app.utils.pagination import Page, PageParams
from app.utils.pdf import format_inr

logger = logging.getLogger(__name__)

RETRY_BASE_MINUTES = 2
MAX_RETRY_DELAY_MINUTES = 60
STALE_SENDING_SECONDS = 600
_SETTLED_FEE_STATUSES = (FeeStatus.PAID, FeeStatus.CANCELLED)


def recipient_for(channel: NotificationChannel, student: Row) -> str | None:
    """WhatsApp and SMS go to the normalised mobile number; email to the student's email
    (students have no email field yet, so email is skipped until one is added)."""
    if channel == NotificationChannel.EMAIL:
        email: str | None = student.get("email")
        return email
    contact: str | None = student.get("contact_e164")
    return contact


class NotificationService:
    def __init__(
        self, db: Database, providers: dict[NotificationChannel, NotificationProvider]
    ) -> None:
        self.db = db
        self.providers = providers

    @property
    def available_channels(self) -> list[str]:
        return sorted(channel.value for channel in self.providers)

    # ------------------------------------------------------------------ enqueue
    def enqueue_for_student(
        self,
        conn: DbConnection,
        *,
        student: Row,
        template: NotificationTemplate,
        params: dict[str, str],
        dedupe_prefix: str,
        fee_id: UUID | None = None,
        payment_id: UUID | None = None,
    ) -> int:
        """Queue one message per enabled channel. Returns how many were newly queued."""
        settings = load_setting(conn, SettingKey.NOTIFICATIONS, NotificationSettings)
        repo = NotificationRepository(conn)
        queued = 0
        for channel in settings.channels:
            if channel not in self.providers:
                continue
            recipient = recipient_for(channel, student)
            if not recipient:
                logger.info(
                    "notification skipped: student has no address for this channel",
                    extra={
                        "student_id": str(student["id"]),
                        "channel": channel.value,
                        "template": template.value,
                    },
                )
                continue
            row = repo.enqueue(
                student_id=student["id"],
                fee_id=fee_id,
                payment_id=payment_id,
                channel=channel.value,
                recipient=recipient,
                template=template.value,
                payload=params,
                dedupe_key=f"{dedupe_prefix}:{channel.value}",
            )
            if row is not None:
                queued += 1
        return queued

    def enqueue_payment_success(
        self, conn: DbConnection, *, payment: Row, fee: Row, receipt: Row
    ) -> int:
        settings = load_setting(conn, SettingKey.NOTIFICATIONS, NotificationSettings)
        if not settings.payment_confirmations_enabled:
            return 0
        student = StudentRepository(conn).get_by_id(payment["student_id"])
        if student is None:
            return 0
        params = {
            "name": student["name"],
            "amount": format_inr(payment["amount_paise"]),
            "fee_title": fee["title"],
            "receipt_number": receipt["receipt_number"],
            "academy_name": load_academy(conn).name,
        }
        return self.enqueue_for_student(
            conn,
            student=student,
            template=NotificationTemplate.PAYMENT_SUCCESS,
            params=params,
            dedupe_prefix=f"payment_success:{payment['id']}",
            fee_id=fee["id"],
            payment_id=payment["id"],
        )

    # ------------------------------------------------------------------ delivery (worker)
    def process_due(self, batch_size: int = 50) -> ProcessResult:
        with self.db.transaction() as conn:
            repo = NotificationRepository(conn)
            recovered = repo.requeue_stale_sending(STALE_SENDING_SECONDS)
            claimed = repo.claim_due(batch_size)
        if recovered:
            logger.warning("requeued stale notifications", extra={"count": recovered})
        result = ProcessResult(claimed=len(claimed))
        for row in claimed:
            outcome = self._deliver(row)
            setattr(result, outcome, getattr(result, outcome) + 1)
        return result

    def _deliver(self, row: Row) -> str:
        if row["template"] == NotificationTemplate.FEE_REMINDER and row["fee_id"]:
            with self.db.transaction() as conn:
                fee = FeeRepository(conn).get_by_id(row["fee_id"])
                if fee is None or fee["status"] in _SETTLED_FEE_STATUSES:
                    NotificationRepository(conn).mark_failed(
                        row["id"], "SKIPPED: the fee is already settled"
                    )
                    return "skipped"

        provider = self.providers.get(NotificationChannel(row["channel"]))
        if provider is None:
            with self.db.transaction() as conn:
                NotificationRepository(conn).mark_failed(row["id"], "CHANNEL_NOT_CONFIGURED")
            return "failed"

        params = {key: str(value) for key, value in (row["payload"] or {}).items()}
        try:
            message = OutgoingMessage(
                recipient=row["recipient"],
                template=row["template"],
                params=params,
                text=render_text(row["template"], params),
            )
            result = provider.send(message)
        except PermanentDeliveryError as exc:
            with self.db.transaction() as conn:
                NotificationRepository(conn).mark_failed(row["id"], exc.message)
            return "failed"
        except Exception as exc:
            if isinstance(exc, AppError):
                error = exc.message
            else:
                error = f"{type(exc).__name__}: {exc}"
                logger.error("notification provider error", exc_info=exc)
            with self.db.transaction() as conn:
                repo = NotificationRepository(conn)
                if row["attempts"] >= row["max_attempts"]:
                    repo.mark_failed(row["id"], error)
                    return "failed"
                delay = min(RETRY_BASE_MINUTES ** row["attempts"], MAX_RETRY_DELAY_MINUTES)
                repo.mark_retry(row["id"], error, datetime.now(UTC) + timedelta(minutes=delay))
            return "retried"

        with self.db.transaction() as conn:
            NotificationRepository(conn).mark_sent(row["id"], result.provider_message_id)
        return "sent"

    def apply_delivery_statuses(
        self, channel: NotificationChannel, statuses: list[DeliveryStatus]
    ) -> int:
        updated = 0
        with self.db.transaction() as conn:
            repo = NotificationRepository(conn)
            for status in statuses:
                if status.status in ("delivered", "read"):
                    updated += repo.mark_delivered(channel.value, status.message_id)
                elif status.status == "failed":
                    updated += repo.mark_delivery_failed(
                        channel.value, status.message_id, status.error or "Delivery failed"
                    )
        return updated

    # ------------------------------------------------------------------ admin
    def search(
        self,
        *,
        status: NotificationStatus | None,
        channel: NotificationChannel | None,
        student_id: UUID | None,
        params: PageParams,
    ) -> Page[Notification]:
        with self.db.transaction() as conn:
            rows, total = NotificationRepository(conn).search(
                status=status.value if status else None,
                channel=channel.value if channel else None,
                student_id=student_id,
                limit=params.limit,
                offset=params.offset,
            )
        return Page([Notification.model_validate(r) for r in rows], total, params)

    def retry(self, actor: CurrentUser, notification_id: UUID) -> Notification:
        with self.db.transaction() as conn:
            repo = NotificationRepository(conn)
            current: dict[str, Any] | None = repo.get_by_id(notification_id)
            if current is None:
                raise NotFoundError("Notification was not found.", code="NOTIFICATION_NOT_FOUND")
            row = repo.requeue_failed(notification_id)
            if row is None:
                raise InvalidStateError("Only failed notifications can be retried.")
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="notification.retried",
                entity_type="notification",
                entity_id=notification_id,
                before={"status": current["status"], "last_error": current["last_error"]},
            )
        return Notification.model_validate(row)
