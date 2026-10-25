from datetime import date
from typing import Any
from uuid import UUID

from psycopg import sql

from app.repositories.base import BaseRepository, Row
from app.utils.validators import escape_like

_SELECT = (
    "select s.*, c.name as course_name from students s left join courses c on c.id = s.course_id"
)


class StudentRepository(BaseRepository):
    table = "students"

    def get(self, student_id: UUID) -> Row | None:
        row = self._one(f"{_SELECT} where s.id = %s", (student_id,))
        if row is not None:
            self._attach_fee_status([row])
        return row

    def lock(self, student_id: UUID) -> Row | None:
        return self.get_by_id(student_id, for_update=True)

    def id_no_exists(self, id_no: str) -> bool:
        return (
            self._one("select 1 from students where lower(id_no) = lower(%s)", (id_no,)) is not None
        )

    def get_by_id_no(self, id_no: str) -> Row | None:
        return self._one(f"{_SELECT} where lower(s.id_no) = lower(%s)", (id_no,))

    def existing_id_nos(self, id_nos: list[str]) -> set[str]:
        """Return the lower-cased ID numbers from `id_nos` that already exist."""
        if not id_nos:
            return set()
        rows = self._all(
            "select lower(id_no) as key from students where lower(id_no) = any(%s)",
            ([value.lower() for value in id_nos],),
        )
        return {row["key"] for row in rows}

    def next_sequence_value(self) -> int:
        return int(self._scalar("select nextval('student_id_seq')"))

    def search(
        self,
        *,
        q: str | None,
        course_id: UUID | None,
        batch_id: UUID | None,
        status: str | None,
        teacher_id: UUID | None,
        program: str | None = None,
        has_id: bool | None = None,
        fee_status: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[Row], int]:
        conditions: list[str] = []
        params: list[Any] = []
        if q:
            pattern = f"%{escape_like(q)}%"
            conditions.append(
                "(s.name ilike %s or s.id_no ilike %s or s.contact ilike %s"
                " or s.guardian_name ilike %s)"
            )
            params.extend([pattern] * 4)
        if course_id is not None:
            conditions.append("s.course_id = %s")
            params.append(course_id)
        if status is not None:
            conditions.append("s.status = %s")
            params.append(status)
        if program is not None:
            conditions.append("s.program = %s")
            params.append(program)
        if has_id is True:
            conditions.append("s.id_no is not null")
        elif has_id is False:
            conditions.append("s.id_no is null")
        if fee_status == "UNPAID":
            conditions.append(
                "exists (select 1 from student_monthly_fees smf"
                " where smf.student_id = s.id and smf.status = 'PENDING')"
            )
        elif fee_status == "PAID":
            conditions.append(
                "exists (select 1 from student_monthly_fees smf"
                " where smf.student_id = s.id and smf.period = '2026-10-01'"
                " and smf.status = 'PAID')"
            )

        if batch_id is not None:
            conditions.append(
                "exists (select 1 from batch_students bs"
                " where bs.student_id = s.id and bs.batch_id = %s)"
            )
            params.append(batch_id)
        if teacher_id is not None:
            conditions.append(
                "exists (select 1 from batch_students bs join batches b on b.id = bs.batch_id"
                " where bs.student_id = s.id and b.teacher_id = %s)"
            )
            params.append(teacher_id)
        where = f"where {' and '.join(conditions)}" if conditions else ""
        total = self._scalar(f"select count(*) from students s {where}", params)
        rows = self._all(
            f"{_SELECT} {where} order by lower(s.name), s.id_no nulls last limit %s offset %s",
            [*params, limit, offset],
        )
        self._attach_fee_status(rows)
        return rows, int(total or 0)

    def _attach_fee_status(self, rows: list[Row]) -> None:
        if not rows:
            return
        student_ids = [r["id"] for r in rows]
        fees = self._all(
            """
            select student_id, period, period_label, status, amount_paise
            from student_monthly_fees
            where student_id = any(%s)
            order by period desc
            """,
            (student_ids,),
        )
        from collections import defaultdict

        paid_periods: dict[UUID, set[date]] = defaultdict(set)
        unpaid_months: dict[UUID, list[str]] = defaultdict(list)
        for f in fees:
            sid = f["student_id"]
            if f["status"] == "PAID":
                paid_periods[sid].add(f["period"])
            else:
                unpaid_months[sid].append(f["period_label"])

        for r in rows:
            sid = r["id"]
            is_paid = date(2026, 10, 1) in paid_periods[sid]
            r["current_month_status"] = "PAID" if is_paid else "UNPAID"
            r["unpaid_months"] = unpaid_months[sid]
            r["due_months_count"] = len(unpaid_months[sid])
            rate = r.get("monthly_fee_paise") or 40000
            r["total_due_paise"] = r["due_months_count"] * rate

        # Also check scheduled fees balance for students who have dues in fees table
        zero_due_ids = [r["id"] for r in rows if r.get("total_due_paise") == 0]
        if zero_due_ids:
            fee_balances = self._all(
                """
                select student_id,
                       sum(greatest(
                           amount_paise - concession_paise - paid_paise, 0
                       )) as balance_paise
                from fees
                where student_id = any(%s) and status in ('PENDING', 'PARTIALLY_PAID', 'OVERDUE')
                group by student_id
                """,
                (zero_due_ids,),
            )
            scheduled_dues = {f["student_id"]: int(f["balance_paise"]) for f in fee_balances}
            for r in rows:
                sid = r["id"]
                if r["total_due_paise"] == 0 and sid in scheduled_dues and scheduled_dues[sid] > 0:
                    r["total_due_paise"] = scheduled_dues[sid]
                    if not r.get("unpaid_months"):
                        r["unpaid_months"] = ["Scheduled Due"]
                        r["due_months_count"] = 1

    def get_unpaid_students(
        self, program: str | None = None, course_id: UUID | None = None
    ) -> list[Row]:
        conditions = [
            "s.status = 'active'",
            (
                "(exists (select 1 from student_monthly_fees smf"
                " where smf.student_id = s.id and smf.status in ('PENDING', 'ABSENT', 'UNPAID'))"
                " or exists (select 1 from fees f"
                " where f.student_id = s.id"
                " and f.status in ('PENDING', 'PARTIALLY_PAID', 'OVERDUE')))"
            ),
        ]

        params: list[Any] = []

        if program is not None:
            conditions.append("s.program = %s")
            params.append(program)
        if course_id is not None:
            conditions.append("s.course_id = %s")
            params.append(course_id)
        where = f"where {' and '.join(conditions)}"
        rows = self._all(
            f"{_SELECT} {where} order by lower(s.name), s.id_no nulls last",
            params,
        )
        self._attach_fee_status(rows)
        return rows

    def insert_many(self, records: list[dict[str, Any]]) -> list[UUID | None]:
        """Insert students in one round of statements, skipping rows that hit a unique
        constraint (ID No. already present). Returns the new id per record, or None."""
        if not records:
            return []
        columns = list(records[0])
        query = sql.SQL(
            "insert into students ({}) values ({}) on conflict do nothing returning id"
        ).format(
            sql.SQL(", ").join(sql.Identifier(col) for col in columns),
            sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        )
        ids: list[UUID | None] = []
        with self.conn.cursor() as cur:
            cur.executemany(query, [tuple(r[c] for c in columns) for r in records], returning=True)
            while True:
                row = cur.fetchone()
                ids.append(row["id"] if row else None)
                if not cur.nextset():
                    break
        if len(ids) != len(records):
            raise RuntimeError("bulk insert returned an unexpected number of results")
        return ids

    def get_monthly_fees(self, student_id: UUID) -> list[Row]:
        return self._all(
            "select * from student_monthly_fees where student_id = %s order by period desc",
            (student_id,),
        )
