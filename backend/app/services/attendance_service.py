"""Attendance marking (teachers for their own batches, admins for all) and reports."""

from datetime import date
from uuid import UUID

from app.core.permissions import CurrentUser, ensure_batch_access, ensure_student_access
from app.db.client import Database
from app.exceptions import NotFoundError, ValidationFailedError
from app.models.attendance import AttendanceRecord, attendance_percentage
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.batch_repository import BatchRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.attendance import (
    AttendanceSummary,
    BatchReportRow,
    MarkAttendanceRequest,
    RosterEntry,
    StudentAttendance,
)
from app.services.audit_service import record_audit
from app.utils.dates import local_today

MAX_RANGE_DAYS = 366


def _check_range(date_from: date, date_to: date) -> None:
    if date_from > date_to:
        raise ValidationFailedError("date_from must not be after date_to.", code="INVALID_RANGE")
    if (date_to - date_from).days > MAX_RANGE_DAYS:
        raise ValidationFailedError("The date range cannot exceed one year.", code="INVALID_RANGE")


class AttendanceService:
    def __init__(self, db: Database, timezone: str) -> None:
        self.db = db
        self.timezone = timezone

    def mark(
        self, user: CurrentUser, batch_id: UUID, payload: MarkAttendanceRequest
    ) -> list[AttendanceRecord]:
        if payload.attendance_date > local_today(self.timezone):
            raise ValidationFailedError(
                "Attendance cannot be marked for a future date.", code="FUTURE_DATE"
            )
        with self.db.transaction() as conn:
            ensure_batch_access(conn, user, batch_id)
            batches = BatchRepository(conn)
            if batches.get_by_id(batch_id) is None:
                raise NotFoundError("Batch was not found.", code="BATCH_NOT_FOUND")
            roster = batches.student_ids(batch_id)
            outsiders = [str(r.student_id) for r in payload.records if r.student_id not in roster]
            if outsiders:
                raise ValidationFailedError(
                    "Some students are not assigned to this batch.",
                    code="STUDENT_NOT_IN_BATCH",
                    details={"student_ids": outsiders},
                )
            repo = AttendanceRepository(conn)
            rows = [
                repo.upsert(
                    batch_id=batch_id,
                    student_id=record.student_id,
                    attendance_date=payload.attendance_date,
                    status=record.status.value,
                    remarks=record.remarks,
                    marked_by=user.user_id,
                )
                for record in payload.records
            ]
            record_audit(
                conn,
                actor_id=user.user_id,
                action="attendance.marked",
                entity_type="batch",
                entity_id=batch_id,
                after={"date": payload.attendance_date.isoformat(), "records": len(rows)},
            )
        return [AttendanceRecord.model_validate(r) for r in rows]

    def roster(self, user: CurrentUser, batch_id: UUID, day: date) -> list[RosterEntry]:
        with self.db.transaction() as conn:
            ensure_batch_access(conn, user, batch_id)
            if BatchRepository(conn).get_by_id(batch_id) is None:
                raise NotFoundError("Batch was not found.", code="BATCH_NOT_FOUND")
            rows = AttendanceRepository(conn).roster(batch_id, day)
        return [RosterEntry.model_validate(r) for r in rows]

    def student_attendance(
        self, user: CurrentUser, student_id: UUID, date_from: date, date_to: date
    ) -> StudentAttendance:
        _check_range(date_from, date_to)
        with self.db.transaction() as conn:
            ensure_student_access(conn, user, student_id)
            if StudentRepository(conn).get_by_id(student_id) is None:
                raise NotFoundError("Student was not found.", code="STUDENT_NOT_FOUND")
            repo = AttendanceRepository(conn)
            counts = repo.counts_for_student(student_id, date_from, date_to)
            records = repo.records_for_student(student_id, date_from, date_to)
        present, late = counts.get("PRESENT", 0), counts.get("LATE", 0)
        absent, excused = counts.get("ABSENT", 0), counts.get("EXCUSED", 0)
        summary = AttendanceSummary(
            student_id=student_id,
            date_from=date_from,
            date_to=date_to,
            present=present,
            late=late,
            absent=absent,
            excused=excused,
            total=present + late + absent + excused,
            percentage=attendance_percentage(present=present, late=late, absent=absent),
        )
        return StudentAttendance(
            summary=summary, records=[AttendanceRecord.model_validate(r) for r in records]
        )

    def batch_report(
        self, user: CurrentUser, batch_id: UUID, date_from: date, date_to: date
    ) -> list[BatchReportRow]:
        _check_range(date_from, date_to)
        with self.db.transaction() as conn:
            ensure_batch_access(conn, user, batch_id)
            if BatchRepository(conn).get_by_id(batch_id) is None:
                raise NotFoundError("Batch was not found.", code="BATCH_NOT_FOUND")
            rows = AttendanceRepository(conn).batch_report(batch_id, date_from, date_to)
        return [
            BatchReportRow(
                **{k: row[k] for k in ("student_id", "id_no", "name")},
                present=row["present"],
                late=row["late"],
                absent=row["absent"],
                excused=row["excused"],
                percentage=attendance_percentage(
                    present=row["present"], late=row["late"], absent=row["absent"]
                ),
            )
            for row in rows
        ]
