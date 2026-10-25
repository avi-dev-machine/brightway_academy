from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class Course(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    duration_months: int | None
    default_fee_paise: int | None
    active: bool
    created_at: datetime
    updated_at: datetime
