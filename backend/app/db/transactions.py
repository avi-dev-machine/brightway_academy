"""Transaction helpers: advisory locks and translation of constraint violations."""

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager

from psycopg import errors as pg_errors

from app.db.client import DbConnection
from app.exceptions import AppError

_CONSTRAINT_ERRORS = (
    pg_errors.UniqueViolation,
    pg_errors.ForeignKeyViolation,
    pg_errors.CheckViolation,
)


def advisory_xact_lock(conn: DbConnection, key: str) -> None:
    """Serialize work on `key` until the current transaction ends."""
    conn.execute("select pg_advisory_xact_lock(hashtext(%s))", (key,))


def try_advisory_lock(conn: DbConnection, key: str) -> bool:
    """Session-level lock; returns False immediately if another session holds it."""
    row = conn.execute("select pg_try_advisory_lock(hashtext(%s)) as locked", (key,)).fetchone()
    return bool(row and row["locked"])


def release_advisory_lock(conn: DbConnection, key: str) -> None:
    conn.execute("select pg_advisory_unlock(hashtext(%s))", (key,))


@contextmanager
def translate_constraint_errors(mapping: Mapping[str, Callable[[], AppError]]) -> Iterator[None]:
    """Convert named unique/FK/check violations into application errors."""
    try:
        yield
    except _CONSTRAINT_ERRORS as exc:
        factory = mapping.get(exc.diag.constraint_name or "")
        if factory is None:
            raise
        raise factory() from exc
