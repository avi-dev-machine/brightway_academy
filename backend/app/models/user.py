from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.core.constants import Role


class UserProfile(BaseModel):
    user_id: UUID
    email: str | None
    role: Role
    student_id: UUID | None
    teacher_id: UUID | None
    active: bool
    created_at: datetime
    updated_at: datetime
