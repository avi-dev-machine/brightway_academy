from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class AttendanceStatus(StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    EXCUSED = "EXCUSED"


class AttendanceRecord(BaseModel):
    id: UUID
    batch_id: UUID
    student_id: UUID
    attendance_date: date
    status: AttendanceStatus
    remarks: str | None
    marked_by: UUID | None
    created_at: datetime
    updated_at: datetime


def attendance_percentage(*, present: int, late: int, absent: int) -> float | None:
    """Late counts as attended; excused days are left out of the denominator."""
    counted = present + late + absent
    if counted == 0:
        return None
    return round((present + late) * 100 / counted, 1)
