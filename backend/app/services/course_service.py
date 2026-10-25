from uuid import UUID

from app.core.permissions import CurrentUser
from app.db.client import Database
from app.db.transactions import translate_constraint_errors
from app.exceptions import ConflictError, NotFoundError
from app.models.course import Course
from app.repositories.course_repository import CourseRepository
from app.schemas.course import CourseCreate, CourseUpdate
from app.services.audit_service import record_audit
from app.utils.pagination import Page, PageParams

_CONSTRAINTS = {
    "courses_code_key": lambda: ConflictError(
        "A course with this code already exists.", code="DUPLICATE_COURSE_CODE"
    ),
    "courses_name_lower_key": lambda: ConflictError(
        "A course with this name already exists.", code="DUPLICATE_COURSE_NAME"
    ),
}


def course_not_found() -> NotFoundError:
    return NotFoundError("Course was not found.", code="COURSE_NOT_FOUND")


class CourseService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def search(self, *, active: bool | None, q: str | None, params: PageParams) -> Page[Course]:
        with self.db.transaction() as conn:
            rows, total = CourseRepository(conn).search(
                active=active, q=q, limit=params.limit, offset=params.offset
            )
        return Page([Course.model_validate(r) for r in rows], total, params)

    def get(self, course_id: UUID) -> Course:
        with self.db.transaction() as conn:
            row = CourseRepository(conn).get_by_id(course_id)
        if row is None:
            raise course_not_found()
        return Course.model_validate(row)

    def create(self, actor: CurrentUser, payload: CourseCreate) -> Course:
        with self.db.transaction() as conn:
            with translate_constraint_errors(_CONSTRAINTS):
                row = CourseRepository(conn).insert(payload.model_dump())
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="course.created",
                entity_type="course",
                entity_id=row["id"],
                after=row,
            )
        return Course.model_validate(row)

    def update(self, actor: CurrentUser, course_id: UUID, payload: CourseUpdate) -> Course:
        changes = payload.model_dump(exclude_unset=True)
        with self.db.transaction() as conn:
            repo = CourseRepository(conn)
            current = repo.get_by_id(course_id, for_update=True)
            if current is None:
                raise course_not_found()
            with translate_constraint_errors(_CONSTRAINTS):
                row = repo.update_fields(course_id, changes)
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="course.updated",
                entity_type="course",
                entity_id=course_id,
                before=current,
                after=row,
            )
        return Course.model_validate(row)
