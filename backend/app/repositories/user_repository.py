from typing import Any
from uuid import UUID

from psycopg import errors as pg_errors
from psycopg import sql

from app.repositories.base import BaseRepository, Row, adapt


class UserRepository(BaseRepository):
    table = "user_profiles"

    def get(self, user_id: UUID, *, for_update: bool = False) -> Row | None:
        query = "select * from user_profiles where user_id = %s"
        if for_update:
            query += " for update"
        return self._one(query, (user_id,))

    def update(self, user_id: UUID, fields: dict[str, Any]) -> Row | None:
        if not fields:
            return self.get(user_id)
        query = sql.SQL("update user_profiles set {} where user_id = %s returning *").format(
            sql.SQL(", ").join(sql.SQL("{} = %s").format(sql.Identifier(c)) for c in fields)
        )
        return self._one(query, (*(adapt(v) for v in fields.values()), user_id))

    def search(
        self, *, role: str | None, active: bool | None, limit: int, offset: int
    ) -> tuple[list[Row], int]:
        conditions: list[str] = []
        params: list[Any] = []
        if role is not None:
            conditions.append("role = %s")
            params.append(role)
        if active is not None:
            conditions.append("active = %s")
            params.append(active)
        where = f"where {' and '.join(conditions)}" if conditions else ""
        total = self._scalar(f"select count(*) from user_profiles {where}", params)
        rows = self._all(
            f"select * from user_profiles {where} order by created_at, user_id limit %s offset %s",
            [*params, limit, offset],
        )
        return rows, int(total or 0)

    def count_active_admins(self) -> int:
        return int(
            self._scalar("select count(*) from user_profiles where role = 'ADMIN' and active") or 0
        )

    def display_name(self, student_id: UUID | None, teacher_id: UUID | None) -> str | None:
        if student_id is not None:
            return self._scalar("select name from students where id = %s", (student_id,))
        if teacher_id is not None:
            return self._scalar("select name from teachers where id = %s", (teacher_id,))
        return None

    def find_by_identifier(self, identifier: str) -> Row | None:
        """Look up user by identifier (e.g. BWADMIN, Student ID like RG240017), email, or linked student ID."""
        q = """
            select u.* from user_profiles u
            left join students s on s.id = u.student_id
            where lower(u.identifier) = lower(%s)
               or lower(u.email) = lower(%s)
               or (s.id_no is not null and lower(s.id_no) = lower(%s))
            limit 1
        """
        return self._one(q, (identifier, identifier, identifier))

    def find_auth_user_id(self, email: str) -> UUID | None:
        """Look up a Supabase Auth user by email (auth.users exists only on Supabase)."""
        try:
            with (
                self.conn.transaction()
            ):  # savepoint: a missing auth schema must not abort the caller
                value = self._scalar(
                    "select id from auth.users where lower(email) = lower(%s) limit 1", (email,)
                )
        except (pg_errors.UndefinedTable, pg_errors.InvalidSchemaName):
            return None
        return value
