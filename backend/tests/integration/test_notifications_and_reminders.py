"""Reminder scheduling/deduplication and the notification delivery pipeline."""

import hashlib
import hmac
import json
from datetime import date, timedelta

import pytest
from pydantic import SecretStr

from app.dependencies import notification_service, payment_service
from app.exceptions import ExternalServiceError
from app.integrations.notifications import PermanentDeliveryError
from app.models.notification import NotificationChannel
from app.schemas.payment import OfflinePaymentRequest
from app.workers.fee_reminders import run_fee_reminders
from app.workers.scheduler import run_cycle
from tests.factories import make_fee, make_student

TODAY = date.today()


def rows(db, query="select * from notifications order by channel", *params):
    with db.transaction() as conn:
        return conn.execute(query, params).fetchall()


def reminders(container, today=TODAY):
    return run_fee_reminders(container.db, notification_service(container), today)


def test_reminder_is_queued_once_per_stage(container, db, student):
    make_fee(
        db,
        student["id"],
        amount_paise=125_000,
        due_date=TODAY + timedelta(days=3),
        title="Nov tuition",
    )
    first = reminders(container)
    assert (first.checked, first.queued) == (1, 2)  # WhatsApp + SMS
    queued = rows(db)
    assert {r["channel"] for r in queued} == {"WHATSAPP", "SMS"}
    assert queued[0]["payload"]["amount"] == "Rs. 1,250.00"
    assert queued[0]["dedupe_key"].startswith(f"fee_reminder:{student['id']}:")

    second = reminders(container)
    assert (second.queued, second.already_sent) == (0, 1)
    assert len(rows(db)) == 2

    later = reminders(container, TODAY + timedelta(days=3))  # due date reached: next stage
    assert later.queued == 2
    assert {r["reminder_stage"] for r in rows(db, "select reminder_stage from fee_reminders")} == {
        "DUE_IN_3_DAYS",
        "DUE_TODAY",
    }


def test_paid_fees_get_no_more_reminders(container, db, student, admin_id):
    from app.core.constants import Role
    from app.core.permissions import CurrentUser

    fee = make_fee(db, student["id"], amount_paise=10_000, due_date=TODAY)
    assert reminders(container).queued == 2
    admin = CurrentUser(user_id=admin_id, role=Role.ADMIN)
    payment_service(container).record_offline_payment(
        admin, fee["id"], OfflinePaymentRequest(amount_paise=10_000, method="CASH")
    )
    assert reminders(container, TODAY + timedelta(days=3)).checked == 0

    # The reminder queued before payment is skipped at delivery time.
    result = notification_service(container).process_due()
    assert result.skipped == 2
    statuses = {r["template"]: r["status"] for r in rows(db)}
    assert statuses == {"fee_reminder": "FAILED", "payment_success": "SENT"}


def test_students_without_a_valid_mobile_are_skipped(container, db):
    student = make_student(db, contact="033 2456 7890")
    make_fee(db, student["id"], due_date=TODAY)
    result = reminders(container)
    assert (result.skipped_no_contact, result.queued) == (1, 0)


def test_reminders_can_be_disabled(container, db, student):
    with db.transaction() as conn:
        conn.execute(
            "update app_settings set value = jsonb_set(value, '{fee_reminders_enabled}', 'false')"
            " where key = 'notifications'"
        )
    make_fee(db, student["id"], due_date=TODAY)
    assert reminders(container).queued == 0


def test_delivery_marks_sent(container, db, student, notifiers):
    make_fee(db, student["id"], amount_paise=5_000, due_date=TODAY, title="Exam fee")
    reminders(container)
    result = notification_service(container).process_due()
    assert (result.claimed, result.sent) == (2, 2)
    assert {r["status"] for r in rows(db)} == {"SENT"}
    assert all(r["provider_message_id"].startswith("log-") for r in rows(db))
    sms = notifiers[NotificationChannel.SMS].sent[0]
    assert sms.recipient == "+919876543210"
    assert "Exam fee" in sms.text and "Rs. 50.00" in sms.text


def test_transient_errors_are_retried_then_fail(container, db, student, notifiers):
    notifiers[NotificationChannel.WHATSAPP].fail_with = ExternalServiceError("WhatsApp is down")
    make_fee(db, student["id"], due_date=TODAY)
    reminders(container)
    service = notification_service(container)
    assert service.process_due().retried == 1
    whatsapp = rows(db, "select * from notifications where channel = 'WHATSAPP'")[0]
    assert whatsapp["status"] == "QUEUED" and whatsapp["attempts"] == 1
    assert whatsapp["last_error"] == "WhatsApp is down"

    for _ in range(2):  # force the retry to be due now and exhaust the attempts
        with db.transaction() as conn:
            conn.execute("update notifications set next_attempt_at = now() where status = 'QUEUED'")
        service.process_due()
    whatsapp = rows(db, "select * from notifications where channel = 'WHATSAPP'")[0]
    assert whatsapp["status"] == "FAILED" and whatsapp["attempts"] == 3


def test_permanent_errors_fail_immediately(container, db, student, notifiers):
    notifiers[NotificationChannel.SMS].fail_with = PermanentDeliveryError("Invalid number")
    make_fee(db, student["id"], due_date=TODAY)
    reminders(container)
    assert notification_service(container).process_due().failed == 1
    sms = rows(db, "select * from notifications where channel = 'SMS'")[0]
    assert (sms["status"], sms["attempts"]) == ("FAILED", 1)


def test_admin_can_retry_a_failed_notification(
    client, container, db, student, notifiers, admin_headers
):
    notifiers[NotificationChannel.SMS].fail_with = PermanentDeliveryError("Invalid number")
    make_fee(db, student["id"], due_date=TODAY)
    reminders(container)
    notification_service(container).process_due()
    failed = client.get("/api/v1/notifications?status=FAILED", headers=admin_headers).json()["data"]
    assert len(failed) == 1
    retried = client.post(f"/api/v1/notifications/{failed[0]['id']}/retry", headers=admin_headers)
    assert retried.json()["data"]["status"] == "QUEUED"
    again = client.post(f"/api/v1/notifications/{failed[0]['id']}/retry", headers=admin_headers)
    assert again.status_code == 409


def test_whatsapp_delivery_webhook(client, container, db, student):
    make_fee(db, student["id"], due_date=TODAY)
    reminders(container)
    notification_service(container).process_due()
    message_id = rows(db, "select * from notifications where channel = 'WHATSAPP'")[0][
        "provider_message_id"
    ]
    body = json.dumps(
        {
            "entry": [
                {"changes": [{"value": {"statuses": [{"id": message_id, "status": "delivered"}]}}]}
            ]
        }
    ).encode()

    not_configured = client.post("/api/v1/notifications/webhooks/whatsapp", content=body)
    assert not_configured.status_code == 503

    container.settings.whatsapp_app_secret = SecretStr("meta-app-secret")
    bad = client.post(
        "/api/v1/notifications/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": "sha256=" + "0" * 64},
    )
    assert bad.status_code == 400
    signature = hmac.new(b"meta-app-secret", body, hashlib.sha256).hexdigest()
    good = client.post(
        "/api/v1/notifications/webhooks/whatsapp",
        content=body,
        headers={"X-Hub-Signature-256": f"sha256={signature}"},
    )
    assert good.status_code == 200, good.text
    whatsapp = rows(db, "select * from notifications where channel = 'WHATSAPP'")[0]
    assert whatsapp["status"] == "DELIVERED" and whatsapp["delivered_at"] is not None


def test_whatsapp_verification_handshake(client, container):
    container.settings.whatsapp_webhook_verify_token = SecretStr("verify-me")
    params = {"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "12345"}
    ok = client.get("/api/v1/notifications/webhooks/whatsapp", params=params)
    assert ok.status_code == 200 and ok.text == "12345"
    wrong = client.get(
        "/api/v1/notifications/webhooks/whatsapp", params={**params, "hub.verify_token": "x"}
    )
    assert wrong.status_code == 403


def test_scheduler_cycle_runs_daily_jobs_and_delivery(container, db, student):
    make_fee(db, student["id"], due_date=TODAY - timedelta(days=3))
    result = run_cycle(container, today=TODAY, run_daily=True)
    assert result["daily"]["overdue_marked"] == 1
    assert result["daily"]["reminders"]["queued"] == 2
    assert result["notifications"]["sent"] == 2
    again = run_cycle(container, today=TODAY, run_daily=True)
    assert again["daily"]["reminders"]["queued"] == 0  # deduplicated


@pytest.mark.parametrize("channels", [["SMS"], []])
def test_channel_settings_are_respected(container, db, student, channels):
    with db.transaction() as conn:
        conn.execute(
            "update app_settings set value = jsonb_set(value, '{channels}', %s::jsonb)"
            " where key = 'notifications'",
            (json.dumps(channels),),
        )
    make_fee(db, student["id"], due_date=TODAY)
    assert reminders(container).queued == len(channels)
