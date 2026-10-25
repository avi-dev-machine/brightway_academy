from datetime import date, datetime
from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

from app.repositories.base import BaseRepository, Row


class NotificationRepository(BaseRepository):
    table = "notifications"

    def enqueue(
        self,
        *,
        student_id: UUID | None,
        fee_id: UUID | None,
        payment_id: UUID | None,
        channel: str,
        recipient: str,
        template: str,
        payload: dict[str, Any],
        dedupe_key: str,
        max_attempts: int = 3,
    ) -> Row | None:
        """Queue a notification. Returns None when the dedupe key was already used."""
        return self._one(
            """
            insert into notifications
                (student_id, fee_id, payment_id, channel, recipient, template, payload,
                 dedupe_key, max_attempts)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (dedupe_key) do nothing
            returning *
            """,
            (
                student_id,
                fee_id,
                payment_id,
                channel,
                recipient,
                template,
                Jsonb(payload),
                dedupe_key,
                max_attempts,
            ),
        )

    def claim_due(self, limit: int) -> list[Row]:
        """Atomically move due QUEUED rows to SENDING. Safe with several workers."""
        return self._all(
            """
            update notifications set status = 'SENDING', attempts = attempts + 1
            where id in (
                select id from notifications
                where status = 'QUEUED' and next_attempt_at <= now()
                order by next_attempt_at
                limit %s
                for update skip locked
            )
            returning *
            """,
            (limit,),
        )

    def requeue_stale_sending(self, older_than_seconds: int) -> int:
        """Recover rows left in SENDING by a crashed worker."""
        cursor = self.conn.execute(
            "update notifications set status = 'QUEUED', next_attempt_at = now()"
            " where status = 'SENDING' and updated_at < now() - make_interval(secs => %s)",
            (older_than_seconds,),
        )
        return cursor.rowcount

    def mark_sent(self, notification_id: UUID, provider_message_id: str | None) -> None:
        self.conn.execute(
            "update notifications set status = 'SENT', provider_message_id = %s,"
            " sent_at = now(), last_error = null where id = %s",
            (provider_message_id, notification_id),
        )

    def mark_retry(self, notification_id: UUID, error: str, next_attempt_at: datetime) -> None:
        self.conn.execute(
            "update notifications set status = 'QUEUED', last_error = %s, next_attempt_at = %s"
            " where id = %s",
            (error[:500], next_attempt_at, notification_id),
        )

    def mark_failed(self, notification_id: UUID, error: str) -> None:
        self.conn.execute(
            "update notifications set status = 'FAILED', last_error = %s where id = %s",
            (error[:500], notification_id),
        )

    def mark_delivered(self, channel: str, provider_message_id: str) -> int:
        cursor = self.conn.execute(
            "update notifications set status = 'DELIVERED', delivered_at = now()"
            " where channel = %s and provider_message_id = %s and status in ('SENDING', 'SENT')",
            (channel, provider_message_id),
        )
        return cursor.rowcount

    def mark_delivery_failed(self, channel: str, provider_message_id: str, error: str) -> int:
        cursor = self.conn.execute(
            "update notifications set status = 'FAILED', last_error = %s"
            " where channel = %s and provider_message_id = %s and status <> 'DELIVERED'",
            (error[:500], channel, provider_message_id),
        )
        return cursor.rowcount

    def requeue_failed(self, notification_id: UUID) -> Row | None:
        return self._one(
            "update notifications set status = 'QUEUED', attempts = 0, next_attempt_at = now(),"
            " last_error = null where id = %s and status = 'FAILED' returning *",
            (notification_id,),
        )

    def search(
        self,
        *,
        status: str | None,
        channel: str | None,
        student_id: UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Row], int]:
        conditions: list[str] = []
        params: list[Any] = []
        for column, value in (("status", status), ("channel", channel), ("student_id", student_id)):
            if value is not None:
                conditions.append(f"{column} = %s")
                params.append(value)
        where = f"where {' and '.join(conditions)}" if conditions else ""
        total = self._scalar(f"select count(*) from notifications {where}", params)
        rows = self._all(
            f"select * from notifications {where} order by created_at desc, id limit %s offset %s",
            [*params, limit, offset],
        )
        return rows, int(total or 0)


class FeeReminderRepository(BaseRepository):
    table = "fee_reminders"

    def record(
        self, *, student_id: UUID, fee_id: UUID, reminder_stage: str, reminder_date: date
    ) -> bool:
        """Record a reminder; False when this exact reminder (dedupe key) already exists."""
        row = self._one(
            "insert into fee_reminders (student_id, fee_id, reminder_stage, reminder_date)"
            " values (%s, %s, %s, %s) on conflict do nothing returning id",
            (student_id, fee_id, reminder_stage, reminder_date),
        )
        return row is not None
