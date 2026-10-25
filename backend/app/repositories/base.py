"""Shared repository helpers.

All values are passed as bound parameters. Table and column identifiers come from code,
never from user input, and are quoted with psycopg.sql.Identifier.
"""

from enum import Enum
from typing import Any
from uuid import UUID

from psycopg import sql
from psycopg.types.json import Jsonb

from app.db.client import DbConnection

Row = dict[str, Any]
Query = str | sql.SQL | sql.Composed


def adapt(value: Any) -> Any:
    """Convert enums to their values and dicts/lists to JSONB before they reach SQL."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict | list):
        return Jsonb(value)
    return value


class BaseRepository:
    table: str = ""

    def __init__(self, conn: DbConnection) -> None:
        self.conn = conn

    def _one(self, query: Query, params: Any = None) -> Row | None:
        return self.conn.execute(query, params).fetchone()

    def _all(self, query: Query, params: Any = None) -> list[Row]:
        return self.conn.execute(query, params).fetchall()

    def _scalar(self, query: Query, params: Any = None) -> Any:
        row = self._one(query, params)
        return next(iter(row.values())) if row else None

    def get_by_id(self, record_id: UUID, *, for_update: bool = False) -> Row | None:
        query = sql.SQL("select * from {} where id = %s").format(sql.Identifier(self.table))
        if for_update:
            query = query + sql.SQL(" for update")
        return self._one(query, (record_id,))

    def insert(self, fields: dict[str, Any]) -> Row:
        query = sql.SQL("insert into {} ({}) values ({}) returning *").format(
            sql.Identifier(self.table),
            sql.SQL(", ").join(sql.Identifier(col) for col in fields),
            sql.SQL(", ").join(sql.Placeholder() for _ in fields),
        )
        row = self._one(query, tuple(adapt(v) for v in fields.values()))
        if row is None:
            raise RuntimeError(f"insert into {self.table} returned no row")
        return row

    def update_fields(self, record_id: UUID, fields: dict[str, Any]) -> Row | None:
        if not fields:
            return self.get_by_id(record_id)
        query = sql.SQL("update {} set {} where id = %s returning *").format(
            sql.Identifier(self.table),
            sql.SQL(", ").join(sql.SQL("{} = %s").format(sql.Identifier(col)) for col in fields),
        )
        return self._one(query, (*(adapt(v) for v in fields.values()), record_id))
