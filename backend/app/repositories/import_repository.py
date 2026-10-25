from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

from app.repositories.base import BaseRepository, Row


class ImportJobRepository(BaseRepository):
    table = "import_jobs"

    def find_completed_by_sha(self, file_sha256: str) -> Row | None:
        return self._one(
            "select * from import_jobs where file_sha256 = %s and status = 'COMPLETED'"
            " order by confirmed_at desc limit 1",
            (file_sha256,),
        )

    def count_completed(self) -> int:
        return int(self._scalar("select count(*) from import_jobs where status = 'COMPLETED'") or 0)

    def list_jobs(self, *, limit: int, offset: int) -> tuple[list[Row], int]:
        total = self._scalar("select count(*) from import_jobs")
        rows = self._all(
            "select * from import_jobs order by created_at desc, id limit %s offset %s",
            (limit, offset),
        )
        return rows, int(total or 0)

    def add_rows(self, job_id: UUID, rows: list[dict[str, Any]]) -> None:
        with self.conn.cursor() as cur:
            cur.executemany(
                "insert into import_job_rows"
                " (job_id, row_number, raw, normalized, status, messages)"
                " values (%s, %s, %s, %s, %s, %s)",
                [
                    (
                        job_id,
                        row["row_number"],
                        Jsonb(row["raw"]),
                        Jsonb(row["normalized"]),
                        row["status"],
                        Jsonb(row["messages"]),
                    )
                    for row in rows
                ],
            )

    def rows(
        self, job_id: UUID, *, status: str | None, limit: int, offset: int
    ) -> tuple[list[Row], int]:
        params: list[Any] = [job_id]
        status_filter = ""
        if status is not None:
            status_filter = " and status = %s"
            params.append(status)
        total = self._scalar(
            f"select count(*) from import_job_rows where job_id = %s{status_filter}", params
        )
        rows = self._all(
            f"select * from import_job_rows where job_id = %s{status_filter}"
            " order by row_number limit %s offset %s",
            [*params, limit, offset],
        )
        return rows, int(total or 0)

    def all_rows(self, job_id: UUID) -> list[Row]:
        return self._all(
            "select * from import_job_rows where job_id = %s order by row_number", (job_id,)
        )

    def set_outcomes(
        self, outcomes: list[tuple[UUID, str, UUID | None, list[dict[str, Any]]]]
    ) -> None:
        """outcomes: (row id, outcome, student id, messages)."""
        if not outcomes:
            return
        with self.conn.cursor() as cur:
            cur.executemany(
                "update import_job_rows set outcome = %s, student_id = %s, messages = %s"
                " where id = %s",
                [
                    (outcome, student_id, Jsonb(messages), row_id)
                    for row_id, outcome, student_id, messages in outcomes
                ],
            )
