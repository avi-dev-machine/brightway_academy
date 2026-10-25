from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Teacher(BaseModel):
    id: UUID
    name: str
    phone: str | None
    email: str | None
    active: bool
    created_at: datetime
    updated_at: datetime
