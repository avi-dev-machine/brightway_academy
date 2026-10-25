from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

from app.repositories.base import BaseRepository, Row


class AuditRepository(BaseRepository):
    table = "audit_logs"

    def add(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        entity_type: str,
        entity_id: str | None,
        before: Any,
        after: Any,
        request_id: str | None,
    ) -> None:
        self.conn.execute(
            "insert into audit_logs "
            "(actor_user_id, action, entity_type, entity_id, before, after, request_id) "
            "values (%s, %s, %s, %s, %s, %s, %s)",
            (
                actor_user_id,
                action,
                entity_type,
                entity_id,
                Jsonb(before) if before is not None else None,
                Jsonb(after) if after is not None else None,
                request_id,
            ),
        )

    def search(
        self,
        *,
        entity_type: str | None,
        entity_id: str | None,
        actor_user_id: UUID | None,
        action: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Row], int]:
        conditions: list[str] = []
        params: list[Any] = []
        for column, value in (
            ("entity_type", entity_type),
            ("entity_id", entity_id),
            ("actor_user_id", actor_user_id),
            ("action", action),
        ):
            if value is not None:
                conditions.append(f"{column} = %s")
                params.append(value)
        where = f"where {' and '.join(conditions)}" if conditions else ""
        total = self._scalar(f"select count(*) from audit_logs {where}", params)
        rows = self._all(
            f"select * from audit_logs {where} order by created_at desc, id limit %s offset %s",
            [*params, limit, offset],
        )
        return rows, int(total or 0)
