from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.attendance import AttendanceRecord, AttendanceStatus


class AttendanceEntry(BaseModel):
    student_id: UUID
    status: AttendanceStatus
    remarks: str | None = Field(default=None, max_length=200)


class MarkAttendanceRequest(BaseModel):
    attendance_date: date
    records: list[AttendanceEntry] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _unique_students(self) -> "MarkAttendanceRequest":
        ids = [record.student_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("Each student may appear only once.")
        return self


class RosterEntry(BaseModel):
    student_id: UUID
    id_no: str
    name: str
    status: AttendanceStatus | None
    remarks: str | None


class AttendanceSummary(BaseModel):
    student_id: UUID
    date_from: date
    date_to: date
    present: int
    late: int
    absent: int
    excused: int
    total: int
    percentage: float | None


class StudentAttendance(BaseModel):
    summary: AttendanceSummary
    records: list[AttendanceRecord]


class BatchReportRow(BaseModel):
    student_id: UUID
    id_no: str
    name: str
    present: int
    late: int
    absent: int
    excused: int
    percentage: float | None
