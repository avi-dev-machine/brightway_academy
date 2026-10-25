from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter

from app.dependencies import ContainerDep, CurrentUserDep, StaffUser, attendance_service
from app.models.attendance import AttendanceRecord
from app.schemas.attendance import (
    BatchReportRow,
    MarkAttendanceRequest,
    RosterEntry,
    StudentAttendance,
)
from app.schemas.common import ApiResponse, ok
from app.utils.dates import local_today

router = APIRouter()

DEFAULT_RANGE_DAYS = 30


def _range(
    container: ContainerDep, date_from: date | None, date_to: date | None
) -> tuple[date, date]:
    end = date_to or local_today(container.settings.timezone)
    return date_from or end - timedelta(days=DEFAULT_RANGE_DAYS), end


@router.post("/batches/{batch_id}", response_model=ApiResponse[list[AttendanceRecord]])
def mark_attendance(
    batch_id: UUID, payload: MarkAttendanceRequest, user: StaffUser, container: ContainerDep
) -> ApiResponse[list[AttendanceRecord]]:
    """Teachers may only mark their own batches. Re-marking a day updates it."""
    return ok(attendance_service(container).mark(user, batch_id, payload))


@router.get("/batches/{batch_id}", response_model=ApiResponse[list[RosterEntry]])
def batch_roster(
    batch_id: UUID, user: StaffUser, container: ContainerDep, day: date | None = None
) -> ApiResponse[list[RosterEntry]]:
    target = day or local_today(container.settings.timezone)
    return ok(attendance_service(container).roster(user, batch_id, target))


@router.get("/batches/{batch_id}/report", response_model=ApiResponse[list[BatchReportRow]])
def batch_report(
    batch_id: UUID,
    user: StaffUser,
    container: ContainerDep,
    date_from: date | None = None,
    date_to: date | None = None,
) -> ApiResponse[list[BatchReportRow]]:
    start, end = _range(container, date_from, date_to)
    return ok(attendance_service(container).batch_report(user, batch_id, start, end))


@router.get("/students/{student_id}", response_model=ApiResponse[StudentAttendance])
def student_attendance(
    student_id: UUID,
    user: CurrentUserDep,
    container: ContainerDep,
    date_from: date | None = None,
    date_to: date | None = None,
) -> ApiResponse[StudentAttendance]:
    start, end = _range(container, date_from, date_to)
    return ok(attendance_service(container).student_attendance(user, student_id, start, end))
