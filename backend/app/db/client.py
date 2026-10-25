"""PostgreSQL connection pool (Supabase Postgres in every deployed environment)."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

DbConnection = Connection[dict[str, Any]]


class Database:
    def __init__(
        self, url: str, *, min_size: int = 1, max_size: int = 10, timeout: float = 30.0
    ) -> None:
        if not url:
            raise ValueError("DATABASE_URL is not configured.")
        self._pool: ConnectionPool[Any] = ConnectionPool(
            conninfo=url,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
            open=False,
            check=ConnectionPool.check_connection,
            # prepare_threshold=None keeps the pool compatible with Supabase's transaction pooler.
            kwargs={"row_factory": dict_row, "prepare_threshold": None},
            name="brightway-db",
        )

    def open(self, wait: bool = False) -> None:
        self._pool.open(wait=wait)

    def close(self) -> None:
        self._pool.close()

    @contextmanager
    def transaction(self, timeout: float | None = None) -> Iterator[DbConnection]:
        """Yield a pooled connection. Commits on success, rolls back on any exception."""
        with self._pool.connection(timeout=timeout) as conn:
            yield conn

    def ping(self) -> bool:
        try:
            with self.transaction(timeout=5.0) as conn:
                conn.execute("select 1")
            return True
        except Exception:
            logger.warning("database ping failed", exc_info=True)
            return False
