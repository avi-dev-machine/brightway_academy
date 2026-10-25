from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.core.constants import Role

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class LoginRequest(BaseModel):
    identifier: str | None = Field(
        default=None, max_length=254, description="Student ID (e.g. RG240017), Admin ID, or Email"
    )
    email: str | None = Field(default=None, max_length=254)
    password: str = Field(min_length=1, max_length=128, description="Passcode or password")

    @property
    def login_id(self) -> str:
        val = (self.identifier or self.email or "").strip()
        if not val:
            raise ValueError("Student ID or Email is required.")
        return val


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10, max_length=4096)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - OAuth token type, not a secret
    expires_in: int
    user_id: UUID


class MeOut(BaseModel):
    user_id: UUID
    email: str | None
    role: Role
    student_id: UUID | None
    teacher_id: UUID | None
    display_name: str | None


def check_role_link(role: Role, student_id: UUID | None, teacher_id: UUID | None) -> None:
    if role == Role.STUDENT and (student_id is None or teacher_id is not None):
        raise ValueError("A STUDENT account must be linked to a student (and no teacher).")
    if role == Role.TEACHER and (teacher_id is None or student_id is not None):
        raise ValueError("A TEACHER account must be linked to a teacher (and no student).")
    if role == Role.ADMIN and (student_id is not None or teacher_id is not None):
        raise ValueError("An ADMIN account cannot be linked to a student or teacher.")


class LinkUserRequest(BaseModel):
    """Grant an existing Supabase Auth user access to the application."""

    user_id: UUID | None = None
    email: str | None = Field(default=None, max_length=254, pattern=EMAIL_PATTERN)
    role: Role
    student_id: UUID | None = None
    teacher_id: UUID | None = None

    @model_validator(mode="after")
    def _validate(self) -> "LinkUserRequest":
        if self.user_id is None and self.email is None:
            raise ValueError("Provide user_id or email.")
        check_role_link(self.role, self.student_id, self.teacher_id)
        return self


class InviteUserRequest(BaseModel):
    email: str = Field(max_length=254, pattern=EMAIL_PATTERN)
    role: Role
    student_id: UUID | None = None
    teacher_id: UUID | None = None

    @model_validator(mode="after")
    def _validate(self) -> "InviteUserRequest":
        check_role_link(self.role, self.student_id, self.teacher_id)
        return self


class UpdateUserRequest(BaseModel):
    active: bool | None = None
    role: Role | None = None
    student_id: UUID | None = None
    teacher_id: UUID | None = None

    @model_validator(mode="after")
    def _validate(self) -> "UpdateUserRequest":
        if self.role is not None:
            check_role_link(self.role, self.student_id, self.teacher_id)
        elif self.student_id is not None or self.teacher_id is not None:
            raise ValueError("Changing the linked student/teacher requires the role as well.")
        return self
