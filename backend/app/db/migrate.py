"""Minimal, checksum-verified SQL migration runner.

Usage (from backend/):
    python -m app.db.migrate status
    python -m app.db.migrate up

Applied migrations are recorded in `schema_migrations`. An applied migration file must
never be edited; add a new numbered migration instead.
"""

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
_FILENAME = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")
_LOCK_KEY = 47_112_026

_BOOTSTRAP_SQL = """
create table if not exists schema_migrations (
    version text primary key,
    name text not null,
    checksum text not null,
    applied_at timestamptz not null default now()
)
"""


class MigrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    sql: str

    @property
    def label(self) -> str:
        return f"{self.version}_{self.name}"

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()


def discover(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    migrations: list[Migration] = []
    for path in sorted(directory.glob("*.sql")):
        match = _FILENAME.match(path.name)
        if not match:
            raise MigrationError(f"Invalid migration filename: {path.name}")
        # Normalise line endings so checksums match across Windows and Linux checkouts.
        sql = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        migrations.append(Migration(match.group(1), match.group(2), sql))
    versions = [m.version for m in migrations]
    if len(versions) != len(set(versions)):
        raise MigrationError("Duplicate migration version numbers found.")
    return migrations


def _applied(conn: psycopg.Connection) -> dict[str, str]:
    exists = conn.execute("select to_regclass('schema_migrations')").fetchone()
    if not exists or exists[0] is None:
        return {}
    rows = conn.execute("select version, checksum from schema_migrations").fetchall()
    return {version: checksum for version, checksum in rows}


def migrate(database_url: str, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations, each in its own transaction. Returns the labels applied."""
    migrations = discover(directory)
    applied_now: list[str] = []
    with psycopg.connect(database_url, autocommit=True, prepare_threshold=None) as conn:
        conn.execute("select pg_advisory_lock(%s)", (_LOCK_KEY,))
        try:
            conn.execute(_BOOTSTRAP_SQL)
            applied = _applied(conn)
            for migration in migrations:
                existing = applied.get(migration.version)
                if existing is not None:
                    if existing != migration.checksum:
                        raise MigrationError(
                            f"Migration {migration.label} was modified after it was applied. "
                            "Create a new migration instead of editing an applied one."
                        )
                    continue
                with conn.transaction():
                    conn.execute(migration.sql)
                    conn.execute(
                        "insert into schema_migrations (version, name, checksum) "
                        "values (%s, %s, %s)",
                        (migration.version, migration.name, migration.checksum),
                    )
                applied_now.append(migration.label)
        finally:
            conn.execute("select pg_advisory_unlock(%s)", (_LOCK_KEY,))
    return applied_now


def status(database_url: str, directory: Path = MIGRATIONS_DIR) -> list[tuple[str, str]]:
    migrations = discover(directory)
    with psycopg.connect(database_url, autocommit=True, prepare_threshold=None) as conn:
        applied = _applied(conn)
    result: list[tuple[str, str]] = []
    for migration in migrations:
        checksum = applied.get(migration.version)
        if checksum is None:
            result.append((migration.label, "pending"))
        elif checksum != migration.checksum:
            result.append((migration.label, "MODIFIED"))
        else:
            result.append((migration.label, "applied"))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Brightway database migrations")
    parser.add_argument("command", choices=["up", "status"])
    args = parser.parse_args(argv)

    from app.config import get_settings

    url = get_settings().database_url.get_secret_value()
    if not url:
        print("DATABASE_URL is not configured.", file=sys.stderr)
        return 2
    try:
        if args.command == "up":
            applied = migrate(url)
            print("Applied: " + ", ".join(applied) if applied else "Database is up to date.")
        else:
            for label, state in status(url):
                print(f"{state:>9}  {label}")
    except MigrationError as exc:
        print(f"Migration error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
