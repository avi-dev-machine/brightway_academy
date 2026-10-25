"""Audit trail. Records are written inside the same transaction as the change they describe."""

from typing import Any
from uuid import UUID

from pydantic_core import to_jsonable_python

from app.db.client import Database, DbConnection
from app.logging import request_id_var
from app.models.audit import AuditLog
from app.repositories.audit_repository import AuditRepository
from app.utils.pagination import Page, PageParams


def _jsonable(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return to_jsonable_python(value)


def record_audit(
    conn: DbConnection,
    *,
    actor_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: Any = None,
    before: Any = None,
    after: Any = None,
) -> None:
    AuditRepository(conn).add(
        actor_user_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        before=_jsonable(before),
        after=_jsonable(after),
        request_id=request_id_var.get(),
    )


class AuditService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def search(
        self,
        *,
        entity_type: str | None,
        entity_id: str | None,
        actor_user_id: UUID | None,
        action: str | None,
        params: PageParams,
    ) -> Page[AuditLog]:
        with self.db.transaction() as conn:
            rows, total = AuditRepository(conn).search(
                entity_type=entity_type,
                entity_id=entity_id,
                actor_user_id=actor_user_id,
                action=action,
                limit=params.limit,
                offset=params.offset,
            )
        return Page([AuditLog.model_validate(r) for r in rows], total, params)
