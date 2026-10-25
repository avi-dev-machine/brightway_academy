from typing import Any

from app.repositories.base import BaseRepository, Row
from app.utils.validators import escape_like


class CourseRepository(BaseRepository):
    table = "courses"

    def search(
        self, *, active: bool | None, q: str | None, limit: int, offset: int
    ) -> tuple[list[Row], int]:
        conditions: list[str] = []
        params: list[Any] = []
        if active is not None:
            conditions.append("active = %s")
            params.append(active)
        if q:
            pattern = f"%{escape_like(q)}%"
            conditions.append("(name ilike %s or code ilike %s)")
            params.extend([pattern, pattern])
        where = f"where {' and '.join(conditions)}" if conditions else ""
        total = self._scalar(f"select count(*) from courses {where}", params)
        rows = self._all(
            f"select * from courses {where} order by lower(name) limit %s offset %s",
            [*params, limit, offset],
        )
        return rows, int(total or 0)

    def all(self) -> list[Row]:
        return self._all("select * from courses order by lower(name)")

    def code_exists(self, code: str) -> bool:
        return self._one("select 1 from courses where code = %s", (code,)) is not None
