from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.student import Student, StudentStatus
from app.utils.validators import normalize_whitespace


class _Normalized(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _normalize(cls, value: Any) -> Any:
        return normalize_whitespace(value) if isinstance(value, str) else value


class StudentCreate(_Normalized):
    id_no: str | None = Field(
        default=None, max_length=50, description="Leave empty to generate the next ID No."
    )
    name: str = Field(min_length=1, max_length=200)
    guardian_name: str | None = Field(default=None, max_length=200)
    address: str | None = Field(default=None, max_length=500)
    contact: str | None = Field(default=None, max_length=100)
    course_id: UUID | None = None
    admission_date: date | None = None


class StudentUpdate(_Normalized):
    id_no: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    guardian_name: str | None = Field(default=None, max_length=200)
    address: str | None = Field(default=None, max_length=500)
    contact: str | None = Field(default=None, max_length=100)
    course_id: UUID | None = None
    admission_date: date | None = None
    status: StudentStatus | None = None
    program: str | None = Field(default=None, max_length=50)
    monthly_fee_paise: int | None = Field(default=None, ge=0)
    fee_notes: str | None = Field(default=None, max_length=500)
    initial_passcode: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def _required_fields_not_cleared(self) -> "StudentUpdate":
        for field in ("name", "status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be empty.")
        if (
            "program" in self.model_fields_set
            and self.program is not None
            and self.program not in ("CERTIFICATE", "NON_CERTIFICATE")
        ):
            raise ValueError("Program must be 'CERTIFICATE' or 'NON_CERTIFICATE'")
        return self


class StudentPhotoResult(BaseModel):
    student: Student
    id_card_generated: bool
    id_card_error: str | None = None


class DueFeeNoticeResult(BaseModel):
    student_id: UUID
    student_name: str
    contact: str | None = None
    contact_e164: str | None = None
    amount_paise: int
    amount_formatted: str
    unpaid_months: list[str] = Field(default_factory=list)
    message_text: str
    whatsapp_url: str | None = None
    queued: bool = True
    notification_id: UUID | None = None


class BroadcastDueNoticeRequest(BaseModel):
    program: str | None = None
    course_id: UUID | None = None
    custom_note: str | None = None


class BroadcastDueNoticeResult(BaseModel):
    total_unpaid: int
    queued_count: int
    skipped_no_contact: int
    message: str
    notified_students: list[DueFeeNoticeResult] = Field(default_factory=list)
