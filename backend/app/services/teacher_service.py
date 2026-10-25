from uuid import UUID

from app.core.permissions import CurrentUser
from app.db.client import Database
from app.db.transactions import translate_constraint_errors
from app.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.teacher import Teacher
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.teacher import TeacherCreate, TeacherUpdate
from app.services.audit_service import record_audit
from app.utils.pagination import Page, PageParams

_CONSTRAINTS = {
    "teachers_email_lower_key": lambda: ConflictError(
        "A teacher with this email already exists.", code="DUPLICATE_TEACHER_EMAIL"
    ),
}


def teacher_not_found() -> NotFoundError:
    return NotFoundError("Teacher was not found.", code="TEACHER_NOT_FOUND")


class TeacherService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def search(self, *, active: bool | None, q: str | None, params: PageParams) -> Page[Teacher]:
        with self.db.transaction() as conn:
            rows, total = TeacherRepository(conn).search(
                active=active, q=q, limit=params.limit, offset=params.offset
            )
        return Page([Teacher.model_validate(r) for r in rows], total, params)

    def get(self, teacher_id: UUID) -> Teacher:
        with self.db.transaction() as conn:
            row = TeacherRepository(conn).get_by_id(teacher_id)
        if row is None:
            raise teacher_not_found()
        return Teacher.model_validate(row)

    def get_own(self, user: CurrentUser) -> Teacher:
        if not user.is_teacher or user.teacher_id is None:
            raise ForbiddenError()
        return self.get(user.teacher_id)

    def create(self, actor: CurrentUser, payload: TeacherCreate) -> Teacher:
        with self.db.transaction() as conn:
            with translate_constraint_errors(_CONSTRAINTS):
                row = TeacherRepository(conn).insert(payload.model_dump())
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="teacher.created",
                entity_type="teacher",
                entity_id=row["id"],
                after=row,
            )
        return Teacher.model_validate(row)

    def update(self, actor: CurrentUser, teacher_id: UUID, payload: TeacherUpdate) -> Teacher:
        changes = payload.model_dump(exclude_unset=True)
        with self.db.transaction() as conn:
            repo = TeacherRepository(conn)
            current = repo.get_by_id(teacher_id, for_update=True)
            if current is None:
                raise teacher_not_found()
            with translate_constraint_errors(_CONSTRAINTS):
                row = repo.update_fields(teacher_id, changes)
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="teacher.updated",
                entity_type="teacher",
                entity_id=teacher_id,
                before=current,
                after=row,
            )
        return Teacher.model_validate(row)
