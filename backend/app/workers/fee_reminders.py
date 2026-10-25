"""Fee reminder job: find unpaid fees, pick the reminder stage, deduplicate, queue messages."""

import logging
from datetime import date, timedelta

from app.db.client import Database
from app.models.notification import NotificationTemplate
from app.models.settings import FeeSettings, NotificationSettings, SettingKey
from app.repositories.fee_repository import FeeRepository
from app.repositories.notification_repository import FeeReminderRepository
from app.schemas.notification import ReminderRunResult
from app.services.notification_service import NotificationService
from app.services.settings_service import load_academy, load_setting
from app.utils.pdf import format_inr

logger = logging.getLogger(__name__)

# How far back to look for unpaid fees beyond the last reminder stage.
LOOKBACK_GRACE_DAYS = 30


def stage_name(offset_days: int) -> str:
    if offset_days < 0:
        return f"DUE_IN_{-offset_days}_DAYS"
    if offset_days == 0:
        return "DUE_TODAY"
    return f"OVERDUE_{offset_days}_DAYS"


def determine_reminder_stage(
    due_date: date, today: date, offsets: list[int]
) -> tuple[str, date] | None:
    """Return the latest reminder stage that has been reached, with its reminder date.

    Only the latest reached stage is returned, so a scheduler that was down for a few
    days sends one catch-up reminder instead of a burst of stale ones.
    """
    days_from_due = (today - due_date).days
    reached = [offset for offset in sorted(offsets) if offset <= days_from_due]
    if not reached:
        return None
    offset = reached[-1]
    return stage_name(offset), due_date + timedelta(days=offset)


def run_fee_reminders(
    db: Database, notifications: NotificationService, today: date
) -> ReminderRunResult:
    result = ReminderRunResult()
    with db.transaction() as conn:
        notification_settings = load_setting(conn, SettingKey.NOTIFICATIONS, NotificationSettings)
        offsets = load_setting(conn, SettingKey.FEES, FeeSettings).reminder_offsets_days
        academy_name = load_academy(conn).name
        if not notification_settings.fee_reminders_enabled or not offsets:
            return result
        fees = FeeRepository(conn).unpaid_for_reminders(
            earliest_due=today - timedelta(days=max(offsets) + LOOKBACK_GRACE_DAYS),
            latest_due=today - timedelta(days=min(offsets)),
        )

    for fee in fees:
        result.checked += 1
        stage = determine_reminder_stage(fee["due_date"], today, offsets)
        if stage is None:
            continue
        if not fee["contact_e164"]:
            result.skipped_no_contact += 1
            continue
        stage_label, reminder_date = stage
        # One transaction per fee: the history row and the queued messages commit together.
        with db.transaction() as conn:
            recorded = FeeReminderRepository(conn).record(
                student_id=fee["student_id"],
                fee_id=fee["id"],
                reminder_stage=stage_label,
                reminder_date=reminder_date,
            )
            if not recorded:
                result.already_sent += 1
                continue
            result.queued += notifications.enqueue_for_student(
                conn,
                student={
                    "id": fee["student_id"],
                    "contact_e164": fee["contact_e164"],
                },
                template=NotificationTemplate.FEE_REMINDER,
                params={
                    "name": fee["student_name"],
                    "fee_title": fee["title"],
                    "amount": format_inr(fee["balance_paise"]),
                    "due_date": f"{fee['due_date']:%d %b %Y}",
                    "academy_name": academy_name,
                },
                dedupe_prefix=(
                    f"fee_reminder:{fee['student_id']}:{fee['id']}:{stage_label}:{reminder_date}"
                ),
                fee_id=fee["id"],
            )
    logger.info("fee reminders run", extra={"operation": "fee_reminders", **result.model_dump()})
    return result
