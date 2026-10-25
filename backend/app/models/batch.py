from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class Batch(BaseModel):
    id: UUID
    course_id: UUID
    course_name: str | None = None
    name: str
    teacher_id: UUID | None
    teacher_name: str | None = None
    start_date: date | None
    end_date: date | None
    schedule: str | None
    capacity: int | None
    active: bool
    student_count: int = 0
    created_at: datetime
    updated_at: datetime
