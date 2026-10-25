"""Recipient selection per channel when enqueueing notifications."""

import json

from app.integrations.notifications import LoggingNotificationProvider
from app.models.notification import NotificationChannel, NotificationTemplate
from app.services.notification_service import NotificationService, recipient_for


def test_recipient_for_channel():
    student = {"id": "s", "contact_e164": "+919876543210"}
    assert recipient_for(NotificationChannel.SMS, student) == "+919876543210"
    assert recipient_for(NotificationChannel.WHATSAPP, student) == "+919876543210"
    assert recipient_for(NotificationChannel.EMAIL, student) is None
    assert recipient_for(NotificationChannel.EMAIL, {**student, "email": "a@b.co"}) == "a@b.co"


def test_registered_email_provider_is_used_only_with_an_address(db, student):
    providers = {
        channel: LoggingNotificationProvider(channel)
        for channel in (NotificationChannel.SMS, NotificationChannel.EMAIL)
    }
    service = NotificationService(db, providers)  # type: ignore[arg-type]
    with db.transaction() as conn:
        conn.execute(
            "update app_settings set value = jsonb_set(value, '{channels}', %s::jsonb)"
            " where key = 'notifications'",
            (json.dumps(["SMS", "EMAIL"]),),
        )
    with db.transaction() as conn:
        queued = service.enqueue_for_student(
            conn,
            student=student,
            template=NotificationTemplate.PAYMENT_SUCCESS,
            params={},
            dedupe_prefix="t1",
        )
    assert queued == 1  # SMS only; no email address on file
    with db.transaction() as conn:
        queued = service.enqueue_for_student(
            conn,
            student={**student, "email": "asha@example.com"},
            template=NotificationTemplate.PAYMENT_SUCCESS,
            params={},
            dedupe_prefix="t2",
        )
        rows = conn.execute(
            "select channel, recipient from notifications where dedupe_key like 't2:%'"
        ).fetchall()
    assert queued == 2
    assert {(r["channel"], r["recipient"]) for r in rows} == {
        ("SMS", "+919876543210"),
        ("EMAIL", "asha@example.com"),
    }
