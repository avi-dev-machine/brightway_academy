"""Test data builders and auth helpers (imported by conftest and tests)."""

from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from typing import Any
from uuid import UUID, uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from PIL import Image

from app.db.client import Database
from app.repositories.base import BaseRepository, Row

TEST_SUPABASE_URL = "https://test-project.supabase.co"
TEST_ISSUER = f"{TEST_SUPABASE_URL}/auth/v1"
SIGNING_KEY = ec.generate_private_key(ec.SECP256R1())


def make_token(
    user_id: UUID,
    *,
    expires_in: int = 3600,
    key: Any = SIGNING_KEY,
    issuer: str = TEST_ISSUER,
    audience: str = "authenticated",
    role: str = "authenticated",
    algorithm: str = "ES256",
    **claims: Any,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "aud": audience,
        "iss": issuer,
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "session_id": str(uuid4()),
        **claims,
    }
    return jwt.encode(payload, key, algorithm=algorithm)


def auth_header(user_id: UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(user_id)}"}


def insert(db: Database, table: str, **fields: Any) -> Row:
    with db.transaction() as conn:
        repo = BaseRepository(conn)
        repo.table = table
        return repo.insert(fields)


_counter = {"n": 0}


def _next() -> int:
    _counter["n"] += 1
    return _counter["n"]


def make_course(
    db: Database, *, code: str | None = None, name: str | None = None, **fields: Any
) -> Row:
    n = _next()
    return insert(db, "courses", code=code or f"C{n}", name=name or f"Course {n}", **fields)


def make_teacher(db: Database, *, name: str = "Ritu Sen", **fields: Any) -> Row:
    return insert(db, "teachers", name=name, **fields)


def make_student(
    db: Database,
    *,
    id_no: str | None = None,
    name: str = "Test Student",
    contact: str | None = "9876543210",
    **fields: Any,
) -> Row:
    from app.utils.validators import normalize_indian_phone

    return insert(
        db,
        "students",
        id_no=id_no or f"T{_next():05d}",
        name=name,
        contact=contact,
        contact_e164=normalize_indian_phone(contact),
        **fields,
    )


def make_batch(db: Database, course_id: UUID, *, name: str | None = None, **fields: Any) -> Row:
    return insert(db, "batches", course_id=course_id, name=name or f"Batch {_next()}", **fields)


def assign_to_batch(db: Database, batch_id: UUID, student_id: UUID) -> None:
    with db.transaction() as conn:
        conn.execute(
            "insert into batch_students (batch_id, student_id) values (%s, %s)",
            (batch_id, student_id),
        )


def make_user(
    db: Database,
    role: str,
    *,
    student_id: UUID | None = None,
    teacher_id: UUID | None = None,
    active: bool = True,
) -> UUID:
    user_id = uuid4()
    insert(
        db,
        "user_profiles",
        user_id=user_id,
        email=f"{user_id.hex[:8]}@example.com",
        role=role,
        student_id=student_id,
        teacher_id=teacher_id,
        active=active,
    )
    return user_id


def make_fee(
    db: Database,
    student_id: UUID,
    *,
    amount_paise: int = 100_000,
    due_date: date | None = None,
    title: str = "Tuition",
    status: str = "PENDING",
    **fields: Any,
) -> Row:
    return insert(
        db,
        "fees",
        student_id=student_id,
        fee_type=fields.pop("fee_type", "ONE_TIME"),
        title=title,
        amount_paise=amount_paise,
        due_date=due_date or date.today() + timedelta(days=10),
        status=status,
        **fields,
    )


def image_bytes(fmt: str = "JPEG", size: tuple[int, int] = (300, 400), mode: str = "RGB") -> bytes:
    buffer = BytesIO()
    Image.new(mode, size, (30, 90, 160) if mode == "RGB" else (30, 90, 160, 128)).save(
        buffer, format=fmt
    )
    return buffer.getvalue()
