"""Authentication (Supabase Auth) and application account management."""

from typing import Any
from uuid import UUID

from app.core.constants import Role
from app.core.permissions import CurrentUser
from app.core.security import TokenClaims
from app.db.client import Database
from app.db.transactions import translate_constraint_errors
from app.exceptions import (
    ConflictError,
    ForbiddenError,
    InvalidStateError,
    NotFoundError,
    StudentNotFoundError,
    UnauthorizedError,
)
from app.integrations.supabase_auth import SupabaseAuthClient
from app.models.user import UserProfile
from app.repositories.student_repository import StudentRepository
from app.repositories.teacher_repository import TeacherRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    InviteUserRequest,
    LinkUserRequest,
    MeOut,
    TokenOut,
    UpdateUserRequest,
)
from app.services.audit_service import record_audit
from app.utils.pagination import Page, PageParams

_PROFILE_CONSTRAINTS = {
    "user_profiles_pkey": lambda: ConflictError(
        "This account is already linked.", code="ACCOUNT_ALREADY_LINKED"
    ),
    "user_profiles_student_id_key": lambda: ConflictError(
        "This student already has a login account.", code="STUDENT_ACCOUNT_EXISTS"
    ),
    "user_profiles_teacher_id_key": lambda: ConflictError(
        "This teacher already has a login account.", code="TEACHER_ACCOUNT_EXISTS"
    ),
}


def _token_out(data: dict[str, Any]) -> TokenOut:
    return TokenOut(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        token_type=data.get("token_type", "bearer"),
        expires_in=int(data.get("expires_in", 3600)),
        user_id=UUID(data["user"]["id"]),
    )


class AuthService:
    def __init__(self, db: Database, auth_client: SupabaseAuthClient) -> None:
        self.db = db
        self.auth_client = auth_client

    # ------------------------------------------------------------------ session
    def load_current_user(self, claims: TokenClaims) -> CurrentUser:
        with self.db.transaction() as conn:
            row = UserRepository(conn).get(claims.user_id)
        if row is None:
            raise ForbiddenError(
                "Your account is not set up yet. Please contact the academy.",
                code="ACCOUNT_NOT_PROVISIONED",
            )
        if not row["active"]:
            raise ForbiddenError("Your account has been disabled.", code="ACCOUNT_DISABLED")
        return CurrentUser(
            user_id=row["user_id"],
            role=Role(row["role"]),
            email=row["email"] or claims.email,
            student_id=row["student_id"],
            teacher_id=row["teacher_id"],
        )

    def login(self, identifier: str, password: str) -> TokenOut:
        from app.core.jwt_signer import issue_token
        from app.core.passwords import verify_password

        identifier = identifier.strip()
        with self.db.transaction() as conn:
            user = UserRepository(conn).find_by_identifier(identifier)

        if user is not None and user.get("password_hash"):
            if not verify_password(password, user["password_hash"]):
                raise UnauthorizedError("Invalid ID or passcode.", code="INVALID_CREDENTIALS")
            if not user["active"]:
                raise ForbiddenError("Your account has been disabled.", code="ACCOUNT_DISABLED")
            return issue_token(user["user_id"], email=user.get("email"))

        try:
            return _token_out(self.auth_client.sign_in_with_password(identifier, password))
        except UnauthorizedError:
            raise
        except Exception:
            raise UnauthorizedError(
                "Invalid ID, email, or passcode.", code="INVALID_CREDENTIALS"
            )

    def refresh(self, refresh_token: str) -> TokenOut:
        if refresh_token.startswith("ref_"):
            parts = refresh_token.split("_")
            if len(parts) == 3:
                try:
                    user_id = UUID(parts[2])
                    with self.db.transaction() as conn:
                        user = UserRepository(conn).get(user_id)
                    if user and user["active"]:
                        from app.core.jwt_signer import issue_token

                        return issue_token(user["user_id"], email=user.get("email"))
                except Exception:
                    pass
        try:
            return _token_out(self.auth_client.refresh_session(refresh_token))
        except Exception:
            raise UnauthorizedError(
                "Session is no longer valid. Please sign in again.", code="INVALID_REFRESH_TOKEN"
            )

    def me(self, user: CurrentUser) -> MeOut:
        with self.db.transaction() as conn:
            name = UserRepository(conn).display_name(user.student_id, user.teacher_id)
        return MeOut(
            user_id=user.user_id,
            email=user.email,
            role=user.role,
            student_id=user.student_id,
            teacher_id=user.teacher_id,
            display_name=name,
        )

    # ------------------------------------------------------------------ account management
    def list_users(
        self, *, role: Role | None, active: bool | None, params: PageParams
    ) -> Page[UserProfile]:
        with self.db.transaction() as conn:
            rows, total = UserRepository(conn).search(
                role=role.value if role else None,
                active=active,
                limit=params.limit,
                offset=params.offset,
            )
        return Page([UserProfile.model_validate(r) for r in rows], total, params)

    def link_user(self, actor: CurrentUser, payload: LinkUserRequest) -> UserProfile:
        with self.db.transaction() as conn:
            users = UserRepository(conn)
            user_id = payload.user_id
            if user_id is None and payload.email:
                user_id = users.find_auth_user_id(payload.email)
                if user_id is None:
                    raise NotFoundError(
                        "No Supabase Auth user exists with this email.", code="AUTH_USER_NOT_FOUND"
                    )
            if user_id is None:
                raise NotFoundError("User was not found.", code="AUTH_USER_NOT_FOUND")
            if users.get(user_id) is not None:
                raise ConflictError(
                    "This account is already linked.", code="ACCOUNT_ALREADY_LINKED"
                )
            self._check_link_targets(conn, payload.student_id, payload.teacher_id)
            with translate_constraint_errors(_PROFILE_CONSTRAINTS):
                row = users.insert(
                    {
                        "user_id": user_id,
                        "email": payload.email,
                        "role": payload.role.value,
                        "student_id": payload.student_id,
                        "teacher_id": payload.teacher_id,
                    }
                )
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="user.linked",
                entity_type="user_profile",
                entity_id=user_id,
                after=row,
            )
        return UserProfile.model_validate(row)

    def invite_user(self, actor: CurrentUser, payload: InviteUserRequest) -> UserProfile:
        with self.db.transaction() as conn:
            self._check_link_targets(conn, payload.student_id, payload.teacher_id)
        user_id = self.auth_client.invite_user(payload.email)
        return self.link_user(
            actor,
            LinkUserRequest(
                user_id=user_id,
                email=payload.email,
                role=payload.role,
                student_id=payload.student_id,
                teacher_id=payload.teacher_id,
            ),
        )

    def update_user(
        self, actor: CurrentUser, user_id: UUID, payload: UpdateUserRequest
    ) -> UserProfile:
        with self.db.transaction() as conn:
            users = UserRepository(conn)
            current = users.get(user_id, for_update=True)
            if current is None:
                raise NotFoundError("User account was not found.", code="USER_NOT_FOUND")
            changes: dict[str, Any] = {}
            if payload.active is not None:
                changes["active"] = payload.active
            if payload.role is not None:
                self._check_link_targets(conn, payload.student_id, payload.teacher_id)
                changes.update(
                    role=payload.role.value,
                    student_id=payload.student_id,
                    teacher_id=payload.teacher_id,
                )
            removes_admin = current["role"] == Role.ADMIN and (
                changes.get("active") is False
                or changes.get("role", Role.ADMIN.value) != Role.ADMIN.value
            )
            if removes_admin and user_id == actor.user_id:
                raise InvalidStateError("You cannot disable or demote your own account.")
            if removes_admin and current["active"] and users.count_active_admins() <= 1:
                raise InvalidStateError("At least one active admin account is required.")
            with translate_constraint_errors(_PROFILE_CONSTRAINTS):
                row = users.update(user_id, changes)
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="user.updated",
                entity_type="user_profile",
                entity_id=user_id,
                before=current,
                after=row,
            )
        return UserProfile.model_validate(row)

    @staticmethod
    def _check_link_targets(conn: Any, student_id: UUID | None, teacher_id: UUID | None) -> None:
        if student_id is not None and StudentRepository(conn).get_by_id(student_id) is None:
            raise StudentNotFoundError()
        if teacher_id is not None and TeacherRepository(conn).get_by_id(teacher_id) is None:
            raise NotFoundError("Teacher was not found.", code="TEACHER_NOT_FOUND")
