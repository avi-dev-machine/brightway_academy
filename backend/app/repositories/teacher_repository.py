from typing import Any

from app.repositories.base import BaseRepository, Row
from app.utils.validators import escape_like


class TeacherRepository(BaseRepository):
    table = "teachers"

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
            conditions.append("(name ilike %s or email ilike %s or phone ilike %s)")
            params.extend([pattern] * 3)
        where = f"where {' and '.join(conditions)}" if conditions else ""
        total = self._scalar(f"select count(*) from teachers {where}", params)
        rows = self._all(
            f"select * from teachers {where} order by lower(name), id limit %s offset %s",
            [*params, limit, offset],
        )
        return rows, int(total or 0)
