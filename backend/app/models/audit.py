from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AuditLog(BaseModel):
    id: UUID
    actor_user_id: UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    request_id: str | None
    created_at: datetime
