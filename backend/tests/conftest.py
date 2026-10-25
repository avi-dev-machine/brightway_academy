"""Shared fixtures.

Database tests run against a disposable local PostgreSQL started with pgserver, or against
TEST_DATABASE_URL (its database name must contain "test": every table is truncated).
Each test starts from empty tables plus the seeded defaults.
"""

import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.security import TokenVerifier
from app.db.client import Database
from app.db.migrate import MIGRATIONS_DIR, migrate
from app.dependencies import Container
from app.integrations.mock_payment import MockPaymentProvider
from app.integrations.notifications import LoggingNotificationProvider, NotificationProvider
from app.integrations.storage.service import StorageService
from app.integrations.supabase_auth import SupabaseAuthClient
from app.main import create_app
from app.models.notification import NotificationChannel
from app.utils.rate_limit import RateLimiter
from tests.factories import (
    SIGNING_KEY,
    TEST_ISSUER,
    TEST_SUPABASE_URL,
    auth_header,
    make_course,
    make_student,
    make_teacher,
    make_user,
)

SEED_SQL = (MIGRATIONS_DIR / "0003_seed_defaults.sql").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        if "test" not in url.rsplit("/", 1)[-1].split("?")[0]:
            pytest.exit(
                "TEST_DATABASE_URL must name a database containing 'test' (tests truncate tables).",
                returncode=2,
            )
        migrate(url)
        yield url
        return
    try:
        import pgserver
    except ImportError:
        pytest.skip("Install pgserver or set TEST_DATABASE_URL to run database tests.")
    data_dir = Path(tempfile.mkdtemp(prefix="brightway-pg-"))
    with pgserver.get_server(data_dir, cleanup_mode="delete") as server:
        server.psql("create database brightway_test;")
        url = server.get_uri().rsplit("/", 1)[0] + "/brightway_test"
        migrate(url)
        yield url


@pytest.fixture(scope="session")
def database(database_url: str) -> Iterator[Database]:
    db = Database(database_url, min_size=1, max_size=4)
    db.open(wait=True)
    yield db
    db.close()


@pytest.fixture
def db(database: Database) -> Database:
    with database.transaction() as conn:
        rows = conn.execute(
            "select tablename from pg_tables where schemaname = current_schema()"
            " and tablename <> 'schema_migrations'"
        ).fetchall()
        conn.execute(
            "truncate table "
            + ", ".join(r["tablename"] for r in rows)
            + " restart identity cascade"
        )
        conn.execute("alter sequence receipt_number_seq restart")
        conn.execute("alter sequence student_id_seq restart")
        conn.execute(SEED_SQL)
    return database


def make_settings(tmp_path: Path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_env": "test",
        "database_url": "postgresql://unused/test",
        "supabase_url": TEST_SUPABASE_URL,
        "supabase_publishable_key": "sb_publishable_test",
        "storage_backend": "local",
        "local_storage_dir": str(tmp_path / "storage"),
        "payment_provider": "mock",
        "cors_origins": "http://localhost:3000",
        "log_level": "WARNING",
        "login_rate_limit_per_minute": 1000,
        "webhook_rate_limit_per_minute": 1000,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[call-arg]


@pytest.fixture
def payment_provider() -> MockPaymentProvider:
    return MockPaymentProvider()


@pytest.fixture
def notifiers() -> dict[NotificationChannel, LoggingNotificationProvider]:
    return {
        NotificationChannel.WHATSAPP: LoggingNotificationProvider(NotificationChannel.WHATSAPP),
        NotificationChannel.SMS: LoggingNotificationProvider(NotificationChannel.SMS),
    }


@pytest.fixture
def container(
    db: Database,
    tmp_path: Path,
    payment_provider: MockPaymentProvider,
    notifiers: dict[NotificationChannel, LoggingNotificationProvider],
) -> Container:
    settings = make_settings(tmp_path)
    public_key = SIGNING_KEY.public_key()
    providers: dict[NotificationChannel, NotificationProvider] = dict(notifiers)
    return Container(
        settings=settings,
        db=db,
        token_verifier=TokenVerifier(issuer=TEST_ISSUER, key_resolver=lambda _token: public_key),
        auth_client=SupabaseAuthClient(TEST_SUPABASE_URL, "sb_publishable_test"),
        storage=StorageService.from_settings(settings),
        payment_provider=payment_provider,
        notification_providers=providers,
        login_limiter=RateLimiter(1000),
        webhook_limiter=RateLimiter(1000),
    )


@pytest.fixture
def client(container: Container) -> Iterator[TestClient]:
    app = create_app(container.settings, container)
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


# ---------------------------------------------------------------------- people
@pytest.fixture
def admin_id(db: Database) -> UUID:
    return make_user(db, "ADMIN")


@pytest.fixture
def admin_headers(admin_id: UUID) -> dict[str, str]:
    return auth_header(admin_id)


@pytest.fixture
def course(db: Database) -> dict[str, Any]:
    return make_course(db, code="DCA", name="Diploma in Computer Applications")


@pytest.fixture
def student(db: Database, course: dict[str, Any]) -> dict[str, Any]:
    return make_student(db, id_no="BCA-001", name="Asha Roy", course_id=course["id"])


@pytest.fixture
def student_headers(db: Database, student: dict[str, Any]) -> dict[str, str]:
    return auth_header(make_user(db, "STUDENT", student_id=student["id"]))


@pytest.fixture
def teacher(db: Database) -> dict[str, Any]:
    return make_teacher(db, name="Ritu Sen", email="ritu@example.com")


@pytest.fixture
def teacher_headers(db: Database, teacher: dict[str, Any]) -> dict[str, str]:
    return auth_header(make_user(db, "TEACHER", teacher_id=teacher["id"]))
