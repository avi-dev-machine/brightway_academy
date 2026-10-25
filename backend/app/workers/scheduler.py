"""Background scheduler, run as its own process (never inside API requests).

    python -m app.workers.scheduler          # loop forever
    python -m app.workers.scheduler --once   # one cycle (e.g. from cron)

Every cycle delivers queued notifications. Once per local day it also marks overdue fees
and queues fee reminders. A PostgreSQL advisory lock ensures only one scheduler runs; it
needs a session-level connection (direct or session-pooler URL, not the transaction pooler).
"""

import argparse
import logging
import signal
import sys
import threading
from datetime import date
from typing import Any

import psycopg

from app.config import get_settings
from app.dependencies import Container, build_container, fee_service, notification_service
from app.logging import configure_logging
from app.utils.dates import local_today
from app.workers.fee_reminders import run_fee_reminders
from app.workers.notification_jobs import process_notifications

logger = logging.getLogger("app.scheduler")

LOCK_KEY = "brightway-scheduler"


def run_daily_jobs(container: Container, today: date) -> dict[str, Any]:
    overdue = fee_service(container).mark_overdue(today)
    reminders = run_fee_reminders(container.db, notification_service(container), today)
    return {"overdue_marked": overdue, "reminders": reminders.model_dump()}


def run_cycle(container: Container, *, today: date, run_daily: bool) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if run_daily:
        result["daily"] = run_daily_jobs(container, today)
    result["notifications"] = process_notifications(notification_service(container)).model_dump()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Brightway background scheduler")
    parser.add_argument("--once", action="store_true", help="run a single cycle and exit")
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(settings.log_level)
    container = build_container(settings)
    container.open()

    lock_conn = psycopg.connect(settings.database_url.get_secret_value(), autocommit=True)
    locked = lock_conn.execute("select pg_try_advisory_lock(hashtext(%s))", (LOCK_KEY,)).fetchone()
    if not locked or not locked[0]:
        logger.warning("another scheduler instance holds the lock; exiting")
        lock_conn.close()
        container.close()
        return 0

    stop = threading.Event()

    def request_stop(signum: int, _frame: object) -> None:
        logger.info("scheduler stopping", extra={"signal": signum})
        stop.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    last_daily_run: date | None = None
    logger.info(
        "scheduler started", extra={"interval_seconds": settings.scheduler_interval_seconds}
    )
    try:
        while not stop.is_set():
            today = local_today(settings.timezone)
            try:
                result = run_cycle(container, today=today, run_daily=last_daily_run != today)
                if "daily" in result:
                    last_daily_run = today
            except Exception:
                # Log and keep going: the next cycle retries; jobs are idempotent.
                logger.exception("scheduler cycle failed")
            if args.once:
                break
            stop.wait(settings.scheduler_interval_seconds)
    finally:
        lock_conn.close()  # closing the session releases the advisory lock
        container.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
