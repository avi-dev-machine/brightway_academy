from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.auth import EMAIL_PATTERN
from app.utils.validators import normalize_whitespace


class _TeacherFields(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _normalize(cls, value: Any) -> Any:
        return normalize_whitespace(value) if isinstance(value, str) else value


class TeacherCreate(_TeacherFields):
    name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=254, pattern=EMAIL_PATTERN)


class TeacherUpdate(_TeacherFields):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=254, pattern=EMAIL_PATTERN)
    active: bool | None = None
