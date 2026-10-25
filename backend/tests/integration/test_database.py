"""Schema-level guarantees: migrations, RLS, data-preservation triggers, constraints."""

import shutil
from pathlib import Path

import psycopg
import pytest

from app.db.migrate import MIGRATIONS_DIR, MigrationError, migrate, status
from tests.factories import make_fee, make_student


def test_migrations_are_idempotent(database_url):
    assert migrate(database_url) == []
    assert all(state == "applied" for _, state in status(database_url))


def test_modified_migration_is_detected(database_url, tmp_path: Path):
    copy = tmp_path / "migrations"
    shutil.copytree(MIGRATIONS_DIR, copy)
    first = sorted(copy.glob("*.sql"))[0]
    first.write_text(first.read_text(encoding="utf-8") + "\n-- edited\n", encoding="utf-8")
    with pytest.raises(MigrationError, match="modified after it was applied"):
        migrate(database_url, copy)


def test_every_table_has_row_level_security(db):
    with db.transaction() as conn:
        rows = conn.execute(
            "select c.relname, c.relrowsecurity from pg_class c"
            " join pg_namespace n on n.oid = c.relnamespace"
            " where n.nspname = current_schema() and c.relkind = 'r'"
        ).fetchall()
    missing = [r["relname"] for r in rows if not r["relrowsecurity"]]
    assert rows and missing == []


@pytest.mark.parametrize("table", ["students", "fees"])
def test_financial_and_student_rows_cannot_be_deleted(db, table):
    student = make_student(db)
    row_id = student["id"] if table == "students" else make_fee(db, student["id"])["id"]
    with (
        pytest.raises(psycopg.errors.RaiseException, match="not allowed"),
        db.transaction() as conn,
    ):
        conn.execute(f"delete from {table} where id = %s", (row_id,))


def test_audit_log_is_append_only(db):
    with db.transaction() as conn:
        conn.execute("insert into audit_logs (action, entity_type) values ('x', 'y')")
    with pytest.raises(psycopg.errors.RaiseException), db.transaction() as conn:
        conn.execute("update audit_logs set action = 'tampered'")


def test_id_no_is_unique_ignoring_case(db):
    make_student(db, id_no="BCA001")
    with pytest.raises(psycopg.errors.UniqueViolation):
        make_student(db, id_no="bca001")


def test_concession_cannot_exceed_amount(db):
    student = make_student(db)
    with pytest.raises(psycopg.errors.CheckViolation):
        make_fee(db, student["id"], amount_paise=1000, concession_paise=2000)


def test_seeded_defaults_exist(db):
    with db.transaction() as conn:
        keys = {r["key"] for r in conn.execute("select key from app_settings").fetchall()}
        template = conn.execute("select name from id_card_templates where is_default").fetchone()
    assert keys == {"academy", "fees", "notifications", "setup"}
    assert template["name"] == "Standard CR80"
