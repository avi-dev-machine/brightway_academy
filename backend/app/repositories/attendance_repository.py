from datetime import date
from uuid import UUID

from app.repositories.base import BaseRepository, Row


class AttendanceRepository(BaseRepository):
    table = "attendance"

    def upsert(
        self,
        *,
        batch_id: UUID,
        student_id: UUID,
        attendance_date: date,
        status: str,
        remarks: str | None,
        marked_by: UUID,
    ) -> Row:
        row = self._one(
            """
            insert into attendance
                (batch_id, student_id, attendance_date, status, remarks, marked_by)
            values (%s, %s, %s, %s, %s, %s)
            on conflict (batch_id, student_id, attendance_date) do update
                set status = excluded.status,
                    remarks = excluded.remarks,
                    marked_by = excluded.marked_by
            returning *
            """,
            (batch_id, student_id, attendance_date, status, remarks, marked_by),
        )
        assert row is not None
        return row

    def roster(self, batch_id: UUID, day: date) -> list[Row]:
        return self._all(
            """
            select s.id as student_id, s.id_no, s.name, a.status, a.remarks
            from batch_students bs
            join students s on s.id = bs.student_id
            left join attendance a
                on a.batch_id = bs.batch_id and a.student_id = s.id and a.attendance_date = %s
            where bs.batch_id = %s
            order by lower(s.name), s.id_no
            """,
            (day, batch_id),
        )

    def counts_for_student(
        self, student_id: UUID, date_from: date, date_to: date
    ) -> dict[str, int]:
        rows = self._all(
            "select status, count(*) as count from attendance"
            " where student_id = %s and attendance_date between %s and %s group by status",
            (student_id, date_from, date_to),
        )
        return {row["status"]: int(row["count"]) for row in rows}

    def records_for_student(self, student_id: UUID, date_from: date, date_to: date) -> list[Row]:
        return self._all(
            "select * from attendance where student_id = %s and attendance_date between %s and %s"
            " order by attendance_date desc, batch_id",
            (student_id, date_from, date_to),
        )

    def batch_report(self, batch_id: UUID, date_from: date, date_to: date) -> list[Row]:
        return self._all(
            """
            select s.id as student_id, s.id_no, s.name,
                   count(a.id) filter (where a.status = 'PRESENT') as present,
                   count(a.id) filter (where a.status = 'LATE') as late,
                   count(a.id) filter (where a.status = 'ABSENT') as absent,
                   count(a.id) filter (where a.status = 'EXCUSED') as excused
            from batch_students bs
            join students s on s.id = bs.student_id
            left join attendance a
                on a.student_id = s.id and a.batch_id = bs.batch_id
               and a.attendance_date between %s and %s
            where bs.batch_id = %s
            group by s.id, s.id_no, s.name
            order by lower(s.name), s.id_no
            """,
            (date_from, date_to, batch_id),
        )
