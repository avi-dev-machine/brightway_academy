"""Import the legacy student CSV from the command line, using the same pipeline as the API.

    python -m scripts.import_initial_csv students.csv --admin-email owner@example.com
    python -m scripts.import_initial_csv students.csv --admin-email owner@example.com --confirm \
        [--skip-errors] [--create-missing-courses]

Without --confirm it only validates and prints the preview (nothing is imported).
"""

import argparse
import json
import sys
from pathlib import Path

from app.config import get_settings
from app.core.constants import Role
from app.core.permissions import CurrentUser
from app.db.client import Database
from app.exceptions import AppError
from app.models.import_job import ImportErrorPolicy
from app.repositories.user_repository import UserRepository
from app.schemas.import_job import ImportConfirmRequest
from app.services.csv_import_service import CsvImportService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Legacy student CSV import")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--admin-email", required=True, help="admin recorded as the importer")
    parser.add_argument("--confirm", action="store_true", help="import after a successful preview")
    parser.add_argument(
        "--skip-errors", action="store_true", help="import valid rows, skip error rows"
    )
    parser.add_argument("--create-missing-courses", action="store_true")
    args = parser.parse_args(argv)

    settings = get_settings()
    db = Database(settings.database_url.get_secret_value(), min_size=1, max_size=2)
    db.open(wait=True)
    try:
        with db.transaction() as conn:
            users = UserRepository(conn)
            user_id = users.find_auth_user_id(args.admin_email)
            profile = users.get(user_id) if user_id else None
        if profile is None or profile["role"] != Role.ADMIN or not profile["active"]:
            print(f"{args.admin_email} is not an active admin.", file=sys.stderr)
            return 1
        actor = CurrentUser(user_id=profile["user_id"], role=Role.ADMIN, email=args.admin_email)
        service = CsvImportService(
            db, max_bytes=settings.max_csv_bytes, max_rows=settings.max_csv_rows
        )

        preview = service.preview(
            actor,
            filename=args.csv_path.name,
            content_type="text/csv",
            data=args.csv_path.read_bytes(),
        )
        print(json.dumps({"job_id": str(preview.job.id), "summary": preview.job.summary}, indent=2))
        for row in preview.problem_rows:
            messages = "; ".join(m["message"] for m in row.messages)
            print(f"  row {row.row_number}: {row.status} - {messages}")
        if not args.confirm:
            print("Preview only. Re-run with --confirm to import.")
            return 0
        job = service.confirm(
            actor,
            preview.job.id,
            ImportConfirmRequest(
                error_policy=ImportErrorPolicy.SKIP_ERRORS
                if args.skip_errors
                else ImportErrorPolicy.STRICT,
                create_missing_courses=args.create_missing_courses,
            ),
        )
        print(json.dumps(job.summary.get("result"), indent=2))
        return 0
    except AppError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        if exc.details:
            print(json.dumps(exc.details, indent=2, default=str), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
