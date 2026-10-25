from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, computed_field


class StudentStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Student(BaseModel):
    id: UUID
    id_no: str | None = None
    name: str
    guardian_name: str | None = None
    address: str | None = None
    contact: str | None = None
    contact_e164: str | None = None
    course_id: UUID | None = None
    course_name: str | None = None
    legacy_course: str | None = None
    admission_date: date | None = None
    status: StudentStatus
    program: str | None = None
    monthly_fee_paise: int | None = None
    fee_notes: str | None = None
    initial_passcode: str | None = None
    issues: list[str] = Field(default_factory=list)
    current_month_status: str | None = None
    unpaid_months: list[str] = Field(default_factory=list)
    due_months_count: int = 0
    total_due_paise: int = 0
    import_job_id: UUID | None = None
    created_at: datetime
    updated_at: datetime
    # Storage paths are internal; files are served through authorised endpoints.
    photo_path: str | None = Field(default=None, exclude=True)
    id_card_path: str | None = Field(default=None, exclude=True)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_photo(self) -> bool:
        return self.photo_path is not None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_id_card(self) -> bool:
        return self.id_card_path is not None


class StudentMonthlyFee(BaseModel):
    id: UUID
    student_id: UUID
    period: date
    period_label: str
    amount_paise: int | None = None
    status: str
    paid_on: date | None = None
    raw_entry: str | None = None
    note: str | None = None
    pending_paise: int | None = None
    created_at: datetime
    updated_at: datetime
