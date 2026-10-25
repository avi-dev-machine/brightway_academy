from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb

from app.repositories.base import BaseRepository


class SettingsRepository(BaseRepository):
    table = "app_settings"

    def get(self, key: str) -> dict[str, Any] | None:
        row = self._one("select value from app_settings where key = %s", (key,))
        return row["value"] if row else None

    def upsert(self, key: str, value: dict[str, Any], updated_by: UUID | None) -> dict[str, Any]:
        row = self._one(
            "insert into app_settings (key, value, updated_by) values (%s, %s, %s)"
            " on conflict (key) do update"
            " set value = excluded.value, updated_by = excluded.updated_by"
            " returning value",
            (key, Jsonb(value), updated_by),
        )
        assert row is not None
        stored: dict[str, Any] = row["value"]
        return stored
