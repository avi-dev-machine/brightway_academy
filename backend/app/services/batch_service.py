from uuid import UUID

from app.core.permissions import CurrentUser, ensure_batch_access
from app.db.client import Database, DbConnection
from app.db.transactions import translate_constraint_errors
from app.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    StudentNotFoundError,
    ValidationFailedError,
)
from app.models.batch import Batch
from app.models.student import Student, StudentStatus
from app.repositories.batch_repository import BatchRepository
from app.repositories.course_repository import CourseRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.batch import BatchAssignmentResult, BatchCreate, BatchUpdate
from app.services.audit_service import record_audit
from app.utils.pagination import Page, PageParams

_CONSTRAINTS = {
    "batches_course_name_key": lambda: ConflictError(
        "This course already has a batch with that name.", code="DUPLICATE_BATCH_NAME"
    ),
}


def batch_not_found() -> NotFoundError:
    return NotFoundError("Batch was not found.", code="BATCH_NOT_FOUND")


class BatchService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def search(
        self,
        user: CurrentUser,
        *,
        course_id: UUID | None,
        teacher_id: UUID | None,
        active: bool | None,
        params: PageParams,
    ) -> Page[Batch]:
        if user.is_student:
            raise ForbiddenError()
        if user.is_teacher:
            teacher_id = user.teacher_id  # teachers only ever see their own batches
        with self.db.transaction() as conn:
            rows, total = BatchRepository(conn).search(
                course_id=course_id,
                teacher_id=teacher_id,
                active=active,
                limit=params.limit,
                offset=params.offset,
            )
        return Page([Batch.model_validate(r) for r in rows], total, params)

    def get(self, user: CurrentUser, batch_id: UUID) -> Batch:
        with self.db.transaction() as conn:
            ensure_batch_access(conn, user, batch_id)
            row = BatchRepository(conn).get(batch_id)
        if row is None:
            raise batch_not_found()
        return Batch.model_validate(row)

    def create(self, actor: CurrentUser, payload: BatchCreate) -> Batch:
        with self.db.transaction() as conn:
            self._check_course(conn, payload.course_id)
            self._check_teacher(conn, payload.teacher_id)
            repo = BatchRepository(conn)
            with translate_constraint_errors(_CONSTRAINTS):
                inserted = repo.insert(payload.model_dump())
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="batch.created",
                entity_type="batch",
                entity_id=inserted["id"],
                after=inserted,
            )
            row = repo.get(inserted["id"])
        return Batch.model_validate(row)

    def update(self, actor: CurrentUser, batch_id: UUID, payload: BatchUpdate) -> Batch:
        changes = payload.model_dump(exclude_unset=True)
        with self.db.transaction() as conn:
            repo = BatchRepository(conn)
            current = repo.get_by_id(batch_id, for_update=True)
            if current is None:
                raise batch_not_found()
            if "teacher_id" in changes:
                self._check_teacher(conn, changes["teacher_id"])
            capacity = changes.get("capacity")
            if capacity is not None and capacity < repo.student_count(batch_id):
                raise ValidationFailedError(
                    "Capacity cannot be lower than the number of assigned students.",
                    code="CAPACITY_TOO_LOW",
                )
            start = changes.get("start_date", current["start_date"])
            end = changes.get("end_date", current["end_date"])
            if start and end and end < start:
                raise ValidationFailedError("end_date must not be before start_date.")
            with translate_constraint_errors(_CONSTRAINTS):
                updated = repo.update_fields(batch_id, changes)
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="batch.updated",
                entity_type="batch",
                entity_id=batch_id,
                before=current,
                after=updated,
            )
            row = repo.get(batch_id)
        return Batch.model_validate(row)

    def list_students(self, user: CurrentUser, batch_id: UUID) -> list[Student]:
        with self.db.transaction() as conn:
            ensure_batch_access(conn, user, batch_id)
            repo = BatchRepository(conn)
            if repo.get_by_id(batch_id) is None:
                raise batch_not_found()
            rows = repo.list_students(batch_id)
        return [Student.model_validate(r) for r in rows]

    def add_students(
        self, actor: CurrentUser, batch_id: UUID, student_ids: list[UUID]
    ) -> BatchAssignmentResult:
        unique_ids = list(dict.fromkeys(student_ids))
        with self.db.transaction() as conn:
            repo = BatchRepository(conn)
            # Locking the batch row serialises concurrent assignments for the capacity check.
            batch = repo.get_by_id(batch_id, for_update=True)
            if batch is None:
                raise batch_not_found()
            if not batch["active"]:
                raise ValidationFailedError("This batch is inactive.", code="BATCH_INACTIVE")
            students = StudentRepository(conn)
            for student_id in unique_ids:
                student = students.get_by_id(student_id)
                if student is None:
                    raise StudentNotFoundError(details={"student_id": str(student_id)})
                if student["status"] != StudentStatus.ACTIVE:
                    raise ValidationFailedError(
                        "Inactive students cannot be assigned to a batch.",
                        code="STUDENT_INACTIVE",
                        details={"student_id": str(student_id)},
                    )
            existing = repo.student_ids(batch_id)
            new_ids = [sid for sid in unique_ids if sid not in existing]
            if batch["capacity"] is not None and len(existing) + len(new_ids) > batch["capacity"]:
                raise ValidationFailedError("The batch is full.", code="BATCH_FULL")
            for student_id in new_ids:
                repo.add_student(batch_id, student_id, actor.user_id)
            if new_ids:
                record_audit(
                    conn,
                    actor_id=actor.user_id,
                    action="batch.students_added",
                    entity_type="batch",
                    entity_id=batch_id,
                    after={"student_ids": [str(s) for s in new_ids]},
                )
        return BatchAssignmentResult(
            added=new_ids, already_assigned=[sid for sid in unique_ids if sid in existing]
        )

    def remove_student(self, actor: CurrentUser, batch_id: UUID, student_id: UUID) -> None:
        with self.db.transaction() as conn:
            if not BatchRepository(conn).remove_student(batch_id, student_id):
                raise NotFoundError(
                    "The student is not assigned to this batch.", code="NOT_IN_BATCH"
                )
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="batch.student_removed",
                entity_type="batch",
                entity_id=batch_id,
                before={"student_id": str(student_id)},
            )

    @staticmethod
    def _check_course(conn: DbConnection, course_id: UUID) -> None:
        if CourseRepository(conn).get_by_id(course_id) is None:
            raise NotFoundError("Course was not found.", code="COURSE_NOT_FOUND")

    @staticmethod
    def _check_teacher(conn: DbConnection, teacher_id: UUID | None) -> None:
        if teacher_id is None:
            return
        teacher = TeacherRepository(conn).get_by_id(teacher_id)
        if teacher is None:
            raise NotFoundError("Teacher was not found.", code="TEACHER_NOT_FOUND")
        if not teacher["active"]:
            raise ValidationFailedError("This teacher is inactive.", code="TEACHER_INACTIVE")
