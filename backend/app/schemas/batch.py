from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.utils.validators import normalize_whitespace


class _BatchFields(BaseModel):
    @field_validator("name", "schedule", mode="before", check_fields=False)
    @classmethod
    def _normalize(cls, value: Any) -> Any:
        return normalize_whitespace(value) if isinstance(value, str) else value

    @model_validator(mode="after")
    def _dates_in_order(self) -> Any:
        start = getattr(self, "start_date", None)
        end = getattr(self, "end_date", None)
        if start and end and end < start:
            raise ValueError("end_date must not be before start_date.")
        return self


class BatchCreate(_BatchFields):
    course_id: UUID
    name: str = Field(min_length=1, max_length=120)
    teacher_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    schedule: str | None = Field(default=None, max_length=200)
    capacity: int | None = Field(default=None, gt=0, le=1000)


class BatchUpdate(_BatchFields):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    teacher_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    schedule: str | None = Field(default=None, max_length=200)
    capacity: int | None = Field(default=None, gt=0, le=1000)
    active: bool | None = None


class BatchStudentsRequest(BaseModel):
    student_ids: list[UUID] = Field(min_length=1, max_length=500)


class BatchAssignmentResult(BaseModel):
    added: list[UUID]
    already_assigned: list[UUID]
