"""Dashboard statistics, fee reports and CSV exports (admin only)."""

import csv
import io
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from app.db.client import Database
from app.exceptions import ValidationFailedError
from app.repositories.report_repository import ReportRepository
from app.schemas.report import (
    CollectionReport,
    CollectionRow,
    CourseCount,
    DashboardStats,
    OutstandingRow,
)
from app.utils.dates import local_today
from app.utils.pagination import Page, PageParams
from app.utils.validators import sanitize_csv_cell

MAX_REPORT_DAYS = 366


def paise_to_rupees(paise: int | None) -> str:
    if paise is None:
        return ""
    sign = "-" if paise < 0 else ""
    rupees, remainder = divmod(abs(paise), 100)
    return f"{sign}{rupees}.{remainder:02d}"


def to_csv(headers: list[str], rows: Iterable[list[Any]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([sanitize_csv_cell(value) for value in row])
    # BOM so Excel opens the UTF-8 file with the right encoding.
    return ("﻿" + buffer.getvalue()).encode("utf-8")


class ReportService:
    def __init__(self, db: Database, timezone: str) -> None:
        self.db = db
        self.timezone = timezone

    def _bounds(self, date_from: date, date_to: date) -> tuple[datetime, datetime]:
        if date_from > date_to:
            raise ValidationFailedError(
                "date_from must not be after date_to.", code="INVALID_RANGE"
            )
        if (date_to - date_from).days > MAX_REPORT_DAYS:
            raise ValidationFailedError(
                "The date range cannot exceed one year.", code="INVALID_RANGE"
            )
        tz = ZoneInfo(self.timezone)
        start = datetime.combine(date_from, time.min, tzinfo=tz)
        end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=tz)
        return start, end

    def dashboard(self) -> DashboardStats:
        today = local_today(self.timezone)
        today_start, today_end = self._bounds(today, today)
        month_start, _ = self._bounds(today.replace(day=1), today)
        with self.db.transaction() as conn:
            repo = ReportRepository(conn)
            students = repo.student_counts()
            by_course = repo.students_by_course()
            fees = repo.fee_totals()
            collected_today = repo.collected_between(today_start, today_end)
            collected_month = repo.collected_between(month_start, today_end)
            attendance = repo.attendance_on(today)
        return DashboardStats(
            students_active=students["active"],
            students_inactive=students["inactive"],
            students_total=students["total"],
            students_by_course=[CourseCount.model_validate(r) for r in by_course],
            fees_outstanding_paise=int(fees["outstanding_paise"]),
            fees_overdue_paise=int(fees["overdue_paise"]),
            fees_overdue_count=int(fees["overdue_count"]),
            collected_today_paise=int(collected_today["amount_paise"]),
            payments_today=int(collected_today["count"]),
            collected_this_month_paise=int(collected_month["amount_paise"]),
            attendance_today_marked=int(attendance["marked"]),
            attendance_today_attended=int(attendance["attended"]),
        )

    def collections(self, date_from: date, date_to: date) -> CollectionReport:
        start, end = self._bounds(date_from, date_to)
        with self.db.transaction() as conn:
            payments = ReportRepository(conn).successful_payments_between(start, end)
        # Grouped by local calendar day in Python, independent of the database's tz data.
        tz = ZoneInfo(self.timezone)
        totals: dict[tuple[date, str, str], list[int]] = defaultdict(lambda: [0, 0])
        for payment in payments:
            key = (payment["paid_at"].astimezone(tz).date(), payment["provider"], payment["method"])
            totals[key][0] += 1
            totals[key][1] += payment["amount_paise"]
        items = [
            CollectionRow(day=day, provider=provider, method=method, count=n, amount_paise=amount)
            for (day, provider, method), (n, amount) in sorted(totals.items())
        ]
        return CollectionReport(
            date_from=date_from,
            date_to=date_to,
            rows=items,
            total_count=sum(r.count for r in items),
            total_paise=sum(r.amount_paise for r in items),
        )

    def outstanding(self, *, course_id: UUID | None, params: PageParams) -> Page[OutstandingRow]:
        with self.db.transaction() as conn:
            rows, total = ReportRepository(conn).outstanding_by_student(
                course_id=course_id, limit=params.limit, offset=params.offset
            )
        return Page([OutstandingRow.model_validate(r) for r in rows], total, params)

    def export_students(self) -> bytes:
        with self.db.transaction() as conn:
            rows = ReportRepository(conn).export_students()
        return to_csv(
            [
                "ID No.",
                "Name",
                "Guardian's Name",
                "Address",
                "Contact No.",
                "Course",
                "Admission Date",
                "Status",
            ],
            (
                [
                    r["id_no"],
                    r["name"],
                    r["guardian_name"],
                    r["address"],
                    r["contact"],
                    r["course"],
                    r["admission_date"],
                    r["status"],
                ]
                for r in rows
            ),
        )

    def export_fees(self) -> bytes:
        with self.db.transaction() as conn:
            rows = ReportRepository(conn).export_fees()
        return to_csv(
            [
                "ID No.",
                "Name",
                "Fee",
                "Type",
                "Amount (INR)",
                "Concession (INR)",
                "Paid (INR)",
                "Balance (INR)",
                "Due Date",
                "Status",
            ],
            (
                [
                    r["id_no"],
                    r["name"],
                    r["title"],
                    r["fee_type"],
                    paise_to_rupees(r["amount_paise"]),
                    paise_to_rupees(r["concession_paise"]),
                    paise_to_rupees(r["paid_paise"]),
                    paise_to_rupees(r["balance_paise"]),
                    r["due_date"],
                    r["status"],
                ]
                for r in rows
            ),
        )

    def export_payments(self, date_from: date, date_to: date) -> bytes:
        start, end = self._bounds(date_from, date_to)
        with self.db.transaction() as conn:
            rows = ReportRepository(conn).export_payments(start, end)
        tz = ZoneInfo(self.timezone)
        return to_csv(
            [
                "Paid At",
                "ID No.",
                "Name",
                "Fee",
                "Amount (INR)",
                "Provider",
                "Method",
                "Status",
                "Provider Payment ID",
                "Reference",
                "Receipt No.",
            ],
            (
                [
                    r["paid_at"].astimezone(tz).isoformat(timespec="minutes")
                    if r["paid_at"]
                    else "",
                    r["id_no"],
                    r["name"],
                    r["title"],
                    paise_to_rupees(r["amount_paise"]),
                    r["provider"],
                    r["method"],
                    r["status"],
                    r["provider_payment_id"],
                    r["reference"],
                    r["receipt_number"],
                ]
                for r in rows
            ),
        )
