from typing import Any
from uuid import UUID

from app.repositories.base import BaseRepository, Row

_SELECT = """
select b.*, c.name as course_name, t.name as teacher_name,
       (select count(*) from batch_students bs where bs.batch_id = b.id) as student_count
from batches b
join courses c on c.id = b.course_id
left join teachers t on t.id = b.teacher_id
"""


class BatchRepository(BaseRepository):
    table = "batches"

    def get(self, batch_id: UUID) -> Row | None:
        return self._one(f"{_SELECT} where b.id = %s", (batch_id,))

    def search(
        self,
        *,
        course_id: UUID | None,
        teacher_id: UUID | None,
        active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Row], int]:
        conditions: list[str] = []
        params: list[Any] = []
        for column, value in (
            ("b.course_id", course_id),
            ("b.teacher_id", teacher_id),
            ("b.active", active),
        ):
            if value is not None:
                conditions.append(f"{column} = %s")
                params.append(value)
        where = f"where {' and '.join(conditions)}" if conditions else ""
        total = self._scalar(f"select count(*) from batches b {where}", params)
        rows = self._all(
            f"{_SELECT} {where} order by lower(b.name), b.id limit %s offset %s",
            [*params, limit, offset],
        )
        return rows, int(total or 0)

    def is_teacher_of_batch(self, teacher_id: UUID, batch_id: UUID) -> bool:
        return (
            self._one(
                "select 1 from batches where id = %s and teacher_id = %s", (batch_id, teacher_id)
            )
            is not None
        )

    def teacher_has_student(self, teacher_id: UUID, student_id: UUID) -> bool:
        return (
            self._one(
                "select 1 from batch_students bs join batches b on b.id = bs.batch_id"
                " where bs.student_id = %s and b.teacher_id = %s limit 1",
                (student_id, teacher_id),
            )
            is not None
        )

    def student_count(self, batch_id: UUID) -> int:
        return int(
            self._scalar("select count(*) from batch_students where batch_id = %s", (batch_id,))
            or 0
        )

    def student_ids(self, batch_id: UUID) -> set[UUID]:
        rows = self._all("select student_id from batch_students where batch_id = %s", (batch_id,))
        return {row["student_id"] for row in rows}

    def add_student(self, batch_id: UUID, student_id: UUID, assigned_by: UUID | None) -> bool:
        row = self._one(
            "insert into batch_students (batch_id, student_id, assigned_by) values (%s, %s, %s)"
            " on conflict do nothing returning batch_id",
            (batch_id, student_id, assigned_by),
        )
        return row is not None

    def remove_student(self, batch_id: UUID, student_id: UUID) -> bool:
        row = self._one(
            "delete from batch_students where batch_id = %s and student_id = %s returning batch_id",
            (batch_id, student_id),
        )
        return row is not None

    def list_students(self, batch_id: UUID) -> list[Row]:
        return self._all(
            "select s.*, c.name as course_name from batch_students bs"
            " join students s on s.id = bs.student_id"
            " left join courses c on c.id = s.course_id"
            " where bs.batch_id = %s order by lower(s.name), s.id_no",
            (batch_id,),
        )
