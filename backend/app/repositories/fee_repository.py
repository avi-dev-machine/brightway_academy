from datetime import date
from typing import Any
from uuid import UUID

from app.repositories.base import BaseRepository, Row

_BALANCE = "greatest(f.amount_paise - f.concession_paise - f.paid_paise, 0)"


class FeePlanRepository(BaseRepository):
    table = "fee_plans"

    def search(self, *, active: bool | None, course_id: UUID | None) -> list[Row]:
        conditions: list[str] = []
        params: list[Any] = []
        if active is not None:
            conditions.append("active = %s")
            params.append(active)
        if course_id is not None:
            conditions.append("course_id = %s")
            params.append(course_id)
        where = f"where {' and '.join(conditions)}" if conditions else ""
        return self._all(f"select * from fee_plans {where} order by lower(name)", params)


class FeeRepository(BaseRepository):
    table = "fees"

    def search(
        self, *, student_id: UUID | None, status: str | None, limit: int, offset: int
    ) -> tuple[list[Row], int]:
        conditions: list[str] = []
        params: list[Any] = []
        if student_id is not None:
            conditions.append("student_id = %s")
            params.append(student_id)
        if status is not None:
            conditions.append("status = %s")
            params.append(status)
        where = f"where {' and '.join(conditions)}" if conditions else ""
        total = self._scalar(f"select count(*) from fees {where}", params)
        rows = self._all(
            f"select * from fees {where} order by due_date desc, created_at desc, id desc limit %s offset %s",
            [*params, limit, offset],
        )
        return rows, int(total or 0)

    def summary_for_student(self, student_id: UUID) -> Row:
        row = self._one(
            f"""
            select coalesce(sum(f.amount_paise), 0) as total_amount_paise,
                   coalesce(sum(f.concession_paise), 0) as total_concession_paise,
                   coalesce(sum(f.paid_paise), 0) as total_paid_paise,
                   coalesce(sum({_BALANCE}), 0) as total_outstanding_paise,
                   count(*) filter (where f.status = 'OVERDUE') as overdue_count,
                   coalesce(sum({_BALANCE}) filter (where f.status = 'OVERDUE'), 0) as overdue_paise
            from fees f
            where f.student_id = %s and f.status <> 'CANCELLED'
            """,
            (student_id,),
        )
        assert row is not None
        return row

    def mark_overdue(self, today: date) -> int:
        cursor = self.conn.execute(
            "update fees set status = 'OVERDUE'"
            " where status in ('PENDING', 'PARTIALLY_PAID') and due_date < %s"
            " and amount_paise - concession_paise - paid_paise > 0",
            (today,),
        )
        return cursor.rowcount

    def unpaid_for_reminders(self, *, earliest_due: date, latest_due: date) -> list[Row]:
        return self._all(
            f"""
            select f.*, {_BALANCE} as balance_paise, s.name as student_name, s.contact_e164
            from fees f
            join students s on s.id = f.student_id
            where f.status in ('PENDING', 'PARTIALLY_PAID', 'OVERDUE')
              and s.status = 'active'
              and f.due_date between %s and %s
              and {_BALANCE} > 0
            order by f.due_date, f.id
            """,
            (earliest_due, latest_due),
        )
