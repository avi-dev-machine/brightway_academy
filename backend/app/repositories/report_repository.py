"""Read-only aggregate queries for dashboards, reports and exports."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from app.repositories.base import BaseRepository, Row

_BALANCE = "greatest(f.amount_paise - f.concession_paise - f.paid_paise, 0)"
_UNPAID = "('PENDING', 'PARTIALLY_PAID', 'OVERDUE')"


class ReportRepository(BaseRepository):
    def student_counts(self) -> Row:
        row = self._one(
            "select count(*) filter (where status = 'active') as active,"
            " count(*) filter (where status = 'inactive') as inactive, count(*) as total"
            " from students"
        )
        assert row is not None
        return row

    def students_by_course(self) -> list[Row]:
        return self._all(
            "select c.id as course_id, coalesce(c.name, 'Unassigned') as course_name,"
            " count(s.id) as count from students s left join courses c on c.id = s.course_id"
            " where s.status = 'active' group by c.id, c.name order by count(s.id) desc, 2"
        )

    def fee_totals(self) -> Row:
        row = self._one(
            f"""
            select coalesce(sum({_BALANCE}), 0) as outstanding_paise,
                   coalesce(sum({_BALANCE}) filter (where f.status = 'OVERDUE'), 0)
                as overdue_paise,
                   count(*) filter (where f.status = 'OVERDUE') as overdue_count
            from fees f where f.status in {_UNPAID}
            """
        )
        assert row is not None
        return row

    def collected_between(self, start: datetime, end: datetime) -> Row:
        row = self._one(
            "select coalesce(sum(amount_paise), 0) as amount_paise, count(*) as count"
            " from payments where status = 'SUCCESS' and paid_at >= %s and paid_at < %s",
            (start, end),
        )
        assert row is not None
        return row

    def attendance_on(self, day: date) -> Row:
        row = self._one(
            "select count(*) as marked,"
            " count(*) filter (where status in ('PRESENT', 'LATE')) as attended"
            " from attendance where attendance_date = %s",
            (day,),
        )
        assert row is not None
        return row

    def successful_payments_between(self, start: datetime, end: datetime) -> list[Row]:
        return self._all(
            "select paid_at, provider, coalesce(method, '') as method, amount_paise from payments"
            " where status = 'SUCCESS' and paid_at >= %s and paid_at < %s order by paid_at",
            (start, end),
        )

    def outstanding_by_student(
        self, *, course_id: UUID | None, limit: int, offset: int
    ) -> tuple[list[Row], int]:
        params: list[Any] = []
        course_filter = ""
        if course_id is not None:
            course_filter = "where s.course_id = %s"
            params.append(course_id)
        base = f"""
            with t as (
                select f.student_id,
                       sum({_BALANCE}) as outstanding_paise,
                       coalesce(sum({_BALANCE}) filter (where f.status = 'OVERDUE'), 0)
                as overdue_paise,
                       min(f.due_date) as oldest_due_date
                from fees f where f.status in {_UNPAID}
                group by f.student_id having sum({_BALANCE}) > 0
            )
            select s.id as student_id, s.id_no, s.name, s.contact, c.name as course_name,
                   t.outstanding_paise, t.overdue_paise, t.oldest_due_date
            from t join students s on s.id = t.student_id
            left join courses c on c.id = s.course_id
            {course_filter}
        """
        total = self._scalar(f"select count(*) from ({base}) x", params)
        rows = self._all(
            f"{base} order by t.outstanding_paise desc, s.id_no limit %s offset %s",
            [*params, limit, offset],
        )
        return rows, int(total or 0)

    def export_students(self) -> list[Row]:
        return self._all(
            "select s.id_no, s.name, s.guardian_name, s.address, s.contact, c.name as course,"
            " s.admission_date, s.status from students s left join courses c on c.id = s.course_id"
            " order by s.id_no"
        )

    def export_fees(self) -> list[Row]:
        return self._all(
            f"select s.id_no, s.name, f.title, f.fee_type, f.amount_paise, f.concession_paise,"
            f" f.paid_paise, {_BALANCE} as balance_paise, f.due_date, f.status"
            " from fees f join students s on s.id = f.student_id order by s.id_no, f.due_date"
        )

    def export_payments(self, start: datetime, end: datetime) -> list[Row]:
        return self._all(
            "select p.paid_at, s.id_no, s.name, f.title, p.amount_paise, p.provider, p.method,"
            " p.status, p.provider_payment_id, p.reference, r.receipt_number"
            " from payments p join students s on s.id = p.student_id join fees f on f.id = p.fee_id"
            " left join receipts r on r.payment_id = p.id"
            " where p.created_at >= %s and p.created_at < %s order by p.created_at",
            (start, end),
        )
