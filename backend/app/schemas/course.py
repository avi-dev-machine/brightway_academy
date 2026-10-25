from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.utils.validators import normalize_whitespace

CODE_PATTERN = r"^[A-Z0-9][A-Z0-9_-]{0,31}$"


class _CourseFields(BaseModel):
    @field_validator("name", "description", mode="before", check_fields=False)
    @classmethod
    def _normalize(cls, value: Any) -> Any:
        return normalize_whitespace(value) if isinstance(value, str) else value


class CourseCreate(_CourseFields):
    code: str = Field(pattern=CODE_PATTERN, description="Short code, e.g. DCA")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    duration_months: int | None = Field(default=None, gt=0, le=120)
    default_fee_paise: int | None = Field(default=None, ge=0, le=10_000_000_00)

    @field_validator("code", mode="before")
    @classmethod
    def _upper_code(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value


class CourseUpdate(_CourseFields):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    duration_months: int | None = Field(default=None, gt=0, le=120)
    default_fee_paise: int | None = Field(default=None, ge=0, le=10_000_000_00)
    active: bool | None = None
