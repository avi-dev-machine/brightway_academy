"""The authenticated user and resource-level access checks (role + ownership)."""

from dataclasses import dataclass
from uuid import UUID

from app.core.constants import Role
from app.db.client import DbConnection
from app.exceptions import ForbiddenError
from app.repositories.batch_repository import BatchRepository


@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    role: Role
    email: str | None = None
    student_id: UUID | None = None
    teacher_id: UUID | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def is_teacher(self) -> bool:
        return self.role == Role.TEACHER

    @property
    def is_student(self) -> bool:
        return self.role == Role.STUDENT


def require_role(user: CurrentUser, *roles: Role) -> None:
    if user.role not in roles:
        raise ForbiddenError()


def ensure_student_access(conn: DbConnection, user: CurrentUser, student_id: UUID) -> None:
    """Admins see everyone, students only themselves, teachers only students in their batches."""
    if user.is_admin:
        return
    if user.is_student and user.student_id == student_id:
        return
    if (
        user.is_teacher
        and user.teacher_id is not None
        and BatchRepository(conn).teacher_has_student(user.teacher_id, student_id)
    ):
        return
    raise ForbiddenError("You do not have access to this student.")


def ensure_batch_access(conn: DbConnection, user: CurrentUser, batch_id: UUID) -> None:
    if user.is_admin:
        return
    if (
        user.is_teacher
        and user.teacher_id is not None
        and BatchRepository(conn).is_teacher_of_batch(user.teacher_id, batch_id)
    ):
        return
    raise ForbiddenError("You do not have access to this batch.")
