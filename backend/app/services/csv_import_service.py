"""Legacy CSV migration: validate -> preview -> admin confirmation -> transactional import.

Independent from StudentService. Rows are never silently discarded: every row of the file
is stored with its status, messages and final outcome (IMPORTED / SKIPPED).
"""

import csv
import hashlib
import io
import re
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.permissions import CurrentUser
from app.db.client import Database, DbConnection
from app.db.transactions import advisory_xact_lock, translate_constraint_errors
from app.exceptions import (
    ConflictError,
    FileValidationError,
    InvalidCSVError,
    InvalidStateError,
    NotFoundError,
)
from app.models.import_job import (
    IMPORTABLE_STATUSES,
    ImportErrorPolicy,
    ImportJob,
    ImportJobStatus,
    ImportRow,
    ImportRowOutcome,
    ImportRowStatus,
)
from app.repositories.base import Row
from app.repositories.course_repository import CourseRepository
from app.repositories.import_repository import ImportJobRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.import_job import ImportConfirmRequest, ImportPreview
from app.services.audit_service import record_audit
from app.utils.file_validation import validate_csv_upload
from app.utils.pagination import Page, PageParams
from app.utils.validators import normalize_indian_phone, normalize_whitespace

FIELD_LABELS: dict[str, str] = {
    "id_no": "ID No.",
    "name": "Name",
    "guardian_name": "Guardian's Name",
    "address": "Address",
    "contact": "Contact No.",
    "course": "Course",
}
# Header text reduced to lowercase letters/digits -> field, so a typographic apostrophe
# (U+2019 in "Guardian's Name") still maps to "guardiansname".
HEADER_KEYS: dict[str, str] = {
    "idno": "id_no",
    "name": "name",
    "guardiansname": "guardian_name",
    "guardianname": "guardian_name",
    "address": "address",
    "contactno": "contact",
    "contactnumber": "contact",
    "course": "course",
}
MAX_LENGTHS: dict[str, int] = {
    "id_no": 50,
    "name": 200,
    "guardian_name": 200,
    "address": 500,
    "contact": 100,
    "course": 120,
}
PROBLEM_ROWS_IN_PREVIEW = 50

# A course created concurrently outside the import (e.g. via the courses API).
_COURSE_CONFLICTS = {
    name: lambda: ConflictError(
        "A course was created at the same time as this import. Please confirm again.",
        code="COURSE_CREATED_CONCURRENTLY",
    )
    for name in ("courses_code_key", "courses_name_lower_key")
}


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.replace("﻿", "").lower())


def course_key(text: str) -> str:
    """Comparison key for course names/codes: "D.C.A." matches "DCA"."""
    return _key(text)


def _msg(level: str, code: str, message: str) -> dict[str, str]:
    return {"level": level, "code": code, "message": message}


# ---------------------------------------------------------------------- parsing (pure)


def decode_csv(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("cp1252")
    except UnicodeDecodeError as exc:
        raise InvalidCSVError(
            "The file is not UTF-8 or Windows-1252 text.", code="INVALID_ENCODING"
        ) from exc


@dataclass
class ParsedRow:
    row_number: int  # spreadsheet row number; the header is row 1
    raw: dict[str, str]
    values: dict[str, str | None]
    cell_count_mismatch: bool = False


@dataclass
class ParsedCsv:
    headers: list[str]
    rows: list[ParsedRow]
    blank_rows: int
    extra_columns: list[str]


def parse_csv(text: str, *, max_rows: int) -> ParsedCsv:
    reader = csv.reader(io.StringIO(text, newline=""))
    try:
        headers = [header.replace("﻿", "").strip() for header in next(reader)]
    except StopIteration as exc:
        raise InvalidCSVError("The CSV file is empty.", code="EMPTY_CSV") from exc
    except csv.Error as exc:
        raise InvalidCSVError(
            f"The CSV header could not be read: {exc}", code="MALFORMED_CSV"
        ) from exc

    fields = [HEADER_KEYS.get(_key(header)) for header in headers]
    present = [f for f in fields if f]
    duplicated = sorted({FIELD_LABELS[f] for f in present if present.count(f) > 1})
    if duplicated:
        raise InvalidCSVError(
            f"Duplicate columns: {', '.join(duplicated)}.", code="DUPLICATE_COLUMNS"
        )
    missing = [label for field, label in FIELD_LABELS.items() if field not in present]
    if missing:
        raise InvalidCSVError(
            f"Missing required columns: {', '.join(missing)}.",
            code="MISSING_COLUMNS",
            details={"missing": missing, "found": headers},
        )
    index = {field: i for i, field in enumerate(fields) if field}
    extra = [
        header for header, field in zip(headers, fields, strict=True) if field is None and header
    ]

    rows: list[ParsedRow] = []
    blank = 0
    try:
        for row_number, record in enumerate(reader, start=2):
            if not any(cell.strip() for cell in record):
                blank += 1
                continue
            if len(rows) >= max_rows:
                raise InvalidCSVError(
                    f"The file has more than {max_rows} rows.", code="TOO_MANY_ROWS"
                )
            raw: dict[str, str] = {}
            for i, cell in enumerate(record):
                name = headers[i] if i < len(headers) and headers[i] else f"column_{i + 1}"
                if name in raw:
                    name = f"{name} (column {i + 1})"
                raw[name] = cell
            values = {
                field: normalize_whitespace(record[i]) if i < len(record) else None
                for field, i in index.items()
            }
            rows.append(ParsedRow(row_number, raw, values, len(record) != len(headers)))
    except csv.Error as exc:
        raise InvalidCSVError(
            f"The CSV file could not be parsed: {exc}", code="MALFORMED_CSV"
        ) from exc
    return ParsedCsv(headers, rows, blank, extra)


# ---------------------------------------------------------------------- assessment (pure)


@dataclass
class RowAssessment:
    row_number: int
    raw: dict[str, str]
    normalized: dict[str, Any]
    status: ImportRowStatus
    messages: list[dict[str, str]]


def build_course_lookup(courses: list[Row]) -> Callable[[str], UUID | None]:
    by_key: dict[str, UUID] = {}
    for course in courses:
        by_key.setdefault(course_key(course["name"]), course["id"])
        by_key.setdefault(course_key(course["code"]), course["id"])
    return lambda text: by_key.get(course_key(text))


def assess_rows(
    rows: list[ParsedRow],
    *,
    existing_keys: set[str],
    course_lookup: Callable[[str], UUID | None],
) -> list[RowAssessment]:
    """Validate each row, detect duplicates (in-file and against the DB) and map courses."""
    groups: dict[str, list[ParsedRow]] = defaultdict(list)
    for row in rows:
        id_no = row.values["id_no"]
        if id_no:
            groups[id_no.lower()].append(row)

    def comparable(row: ParsedRow) -> tuple[str | None, ...]:
        return tuple(row.values[field] for field in FIELD_LABELS)

    results: list[RowAssessment] = []
    for row in rows:
        values = row.values
        errors: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []
        notes: list[dict[str, str]] = []

        if row.cell_count_mismatch:
            warnings.append(
                _msg(
                    "warning",
                    "CELL_COUNT_MISMATCH",
                    "Row has a different number of cells than the header.",
                )
            )
        for field, limit in MAX_LENGTHS.items():
            value = values[field]
            if value and len(value) > limit:
                errors.append(
                    _msg(
                        "error",
                        "VALUE_TOO_LONG",
                        f"{FIELD_LABELS[field]} is longer than {limit} characters.",
                    )
                )
        if not values["id_no"]:
            errors.append(_msg("error", "MISSING_ID_NO", "ID No. is required."))
        if not values["name"]:
            errors.append(_msg("error", "MISSING_NAME", "Name is required."))
        if not values["guardian_name"]:
            warnings.append(_msg("warning", "MISSING_GUARDIAN", "Guardian's Name is empty."))
        if not values["address"]:
            warnings.append(_msg("warning", "MISSING_ADDRESS", "Address is empty."))

        contact_e164 = normalize_indian_phone(values["contact"])
        if not values["contact"]:
            warnings.append(_msg("warning", "MISSING_CONTACT", "Contact No. is empty."))
        elif contact_e164 is None:
            warnings.append(
                _msg(
                    "warning",
                    "INVALID_PHONE",
                    "Contact No. is kept as written but is not a valid Indian mobile number "
                    "for WhatsApp/SMS.",
                )
            )

        course_id: UUID | None = None
        if not values["course"]:
            warnings.append(_msg("warning", "MISSING_COURSE", "Course is empty."))
        else:
            course_id = course_lookup(values["course"])
            if course_id is None:
                warnings.append(
                    _msg(
                        "warning",
                        "UNMAPPED_COURSE",
                        f"Course '{values['course']}' does not match an existing course; "
                        "map it or create it when confirming the import.",
                    )
                )

        key = values["id_no"].lower() if values["id_no"] else None
        group = groups.get(key, []) if key else []
        if errors:
            status = ImportRowStatus.ERROR
        elif key in existing_keys:
            status = ImportRowStatus.EXISTS
            notes.append(
                _msg(
                    "info",
                    "ID_NO_EXISTS",
                    "A student with this ID No. already exists; "
                    "the existing record is not modified.",
                )
            )
        elif len(group) > 1:
            if all(comparable(other) == comparable(group[0]) for other in group):
                if row is group[0]:
                    status = ImportRowStatus.WARNING if warnings else ImportRowStatus.VALID
                else:
                    status = ImportRowStatus.DUPLICATE
                    notes.append(
                        _msg(
                            "info",
                            "DUPLICATE_ROW",
                            f"Identical to row {group[0].row_number}; skipped.",
                        )
                    )
            else:
                status = ImportRowStatus.ERROR
                rows_list = ", ".join(str(other.row_number) for other in group)
                errors.append(
                    _msg(
                        "error",
                        "DUPLICATE_ID_NO",
                        f"ID No. appears in rows {rows_list} with different data.",
                    )
                )
        else:
            status = ImportRowStatus.WARNING if warnings else ImportRowStatus.VALID

        normalized = {
            **values,
            "contact_e164": contact_e164,
            "course_id": str(course_id) if course_id else None,
        }
        results.append(
            RowAssessment(row.row_number, row.raw, normalized, status, errors + warnings + notes)
        )
    return results


def summarize(
    assessments: list[RowAssessment], parsed: ParsedCsv, previous_job: Row | None
) -> dict[str, Any]:
    counts = Counter(a.status for a in assessments)
    unmapped = Counter(
        a.normalized["course"]
        for a in assessments
        if a.status in IMPORTABLE_STATUSES
        and a.normalized["course"]
        and not a.normalized["course_id"]
    )
    return {
        "total_rows": len(assessments),
        "status_counts": {status.value: counts.get(status, 0) for status in ImportRowStatus},
        "importable_rows": counts[ImportRowStatus.VALID] + counts[ImportRowStatus.WARNING],
        "blank_rows_ignored": parsed.blank_rows,
        "extra_columns": parsed.extra_columns,
        "unmapped_courses": [{"course": name, "rows": n} for name, n in sorted(unmapped.items())],
        "previously_imported_job_id": str(previous_job["id"]) if previous_job else None,
    }


def derive_course_code(name: str, exists: Callable[[str], bool]) -> str:
    base = re.sub(r"[^A-Z0-9]+", "-", name.upper()).strip("-")[:28] or "COURSE"
    candidate, suffix = base, 2
    while exists(candidate):
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _safe_filename(filename: str | None) -> str:
    name = re.split(r"[\\/]", filename or "")[-1].strip()
    return (name or "upload.csv")[:200]


# ---------------------------------------------------------------------- service


class CsvImportService:
    def __init__(self, db: Database, *, max_bytes: int, max_rows: int) -> None:
        self.db = db
        self.max_bytes = max_bytes
        self.max_rows = max_rows

    def preview(
        self, actor: CurrentUser, *, filename: str | None, content_type: str | None, data: bytes
    ) -> ImportPreview:
        if len(data) > self.max_bytes:
            raise FileValidationError("The CSV file is too large.", code="FILE_TOO_LARGE")
        validate_csv_upload(filename, content_type, data)
        parsed = parse_csv(decode_csv(data), max_rows=self.max_rows)
        if not parsed.rows:
            raise InvalidCSVError("The CSV file has no data rows.", code="NO_DATA_ROWS")
        sha256 = hashlib.sha256(data).hexdigest()

        with self.db.transaction() as conn:
            lookup = build_course_lookup(CourseRepository(conn).all())
            existing = StudentRepository(conn).existing_id_nos(
                [row.values["id_no"] for row in parsed.rows if row.values["id_no"]]
            )
            assessments = assess_rows(parsed.rows, existing_keys=existing, course_lookup=lookup)
            jobs = ImportJobRepository(conn)
            summary = summarize(assessments, parsed, jobs.find_completed_by_sha(sha256))
            job = jobs.insert(
                {
                    "filename": _safe_filename(filename),
                    "file_sha256": sha256,
                    "status": ImportJobStatus.PREVIEWED,
                    "total_rows": len(assessments),
                    "summary": summary,
                    "created_by": actor.user_id,
                }
            )
            jobs.add_rows(
                job["id"],
                [
                    {
                        "row_number": a.row_number,
                        "raw": a.raw,
                        "normalized": a.normalized,
                        "status": a.status.value,
                        "messages": a.messages,
                    }
                    for a in assessments
                ],
            )
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="import.previewed",
                entity_type="import_job",
                entity_id=job["id"],
                after={"filename": job["filename"], "summary": summary},
            )
            problem_rows = [
                row for row in jobs.all_rows(job["id"]) if row["status"] != ImportRowStatus.VALID
            ][:PROBLEM_ROWS_IN_PREVIEW]
        return ImportPreview(
            job=ImportJob.model_validate(job),
            problem_rows=[ImportRow.model_validate(r) for r in problem_rows],
        )

    def get_job(self, job_id: UUID) -> ImportJob:
        with self.db.transaction() as conn:
            row = ImportJobRepository(conn).get_by_id(job_id)
        if row is None:
            raise NotFoundError("Import job was not found.", code="IMPORT_JOB_NOT_FOUND")
        return ImportJob.model_validate(row)

    def list_jobs(self, params: PageParams) -> Page[ImportJob]:
        with self.db.transaction() as conn:
            rows, total = ImportJobRepository(conn).list_jobs(
                limit=params.limit, offset=params.offset
            )
        return Page([ImportJob.model_validate(r) for r in rows], total, params)

    def list_rows(
        self, job_id: UUID, *, status: ImportRowStatus | None, params: PageParams
    ) -> Page[ImportRow]:
        self.get_job(job_id)
        with self.db.transaction() as conn:
            rows, total = ImportJobRepository(conn).rows(
                job_id,
                status=status.value if status else None,
                limit=params.limit,
                offset=params.offset,
            )
        return Page([ImportRow.model_validate(r) for r in rows], total, params)

    def confirm(self, actor: CurrentUser, job_id: UUID, payload: ImportConfirmRequest) -> ImportJob:
        with self.db.transaction() as conn:
            jobs = ImportJobRepository(conn)
            job = jobs.get_by_id(job_id, for_update=True)
            if job is None:
                raise NotFoundError("Import job was not found.", code="IMPORT_JOB_NOT_FOUND")
            if job["status"] == ImportJobStatus.COMPLETED:
                return ImportJob.model_validate(job)  # confirming twice is safe
            if job["status"] != ImportJobStatus.PREVIEWED:
                raise InvalidStateError("This import job cannot be confirmed.")

            rows = jobs.all_rows(job_id)
            error_rows = [r for r in rows if r["status"] == ImportRowStatus.ERROR]
            if error_rows and payload.error_policy == ImportErrorPolicy.STRICT:
                raise InvalidCSVError(
                    f"{len(error_rows)} row(s) have errors. Fix the file and upload it again, "
                    "or confirm with error_policy SKIP_ERRORS to import only the valid rows.",
                    code="IMPORT_HAS_ERRORS",
                    details={"error_rows": [r["row_number"] for r in error_rows[:200]]},
                )
            importable = [r for r in rows if r["status"] in IMPORTABLE_STATUSES]
            resolved, created = self._resolve_courses(conn, actor, importable, payload)

            records = [
                {
                    "id_no": n["id_no"],
                    "name": n["name"],
                    "guardian_name": n["guardian_name"],
                    "address": n["address"],
                    "contact": n["contact"],
                    "contact_e164": n["contact_e164"],
                    "course_id": resolved.get(course_key(n["course"])) if n["course"] else None,
                    "legacy_course": n["course"],
                    "import_job_id": job_id,
                }
                for n in (row["normalized"] for row in importable)
            ]
            new_ids = StudentRepository(conn).insert_many(records)

            outcomes: list[tuple[UUID, ImportRowOutcome, UUID | None, list[dict[str, Any]]]] = []
            imported = skipped_late_duplicates = 0
            for row, student_id in zip(importable, new_ids, strict=True):
                if student_id is not None:
                    imported += 1
                    outcomes.append(
                        (row["id"], ImportRowOutcome.IMPORTED, student_id, row["messages"])
                    )
                else:
                    skipped_late_duplicates += 1
                    note = _msg(
                        "info",
                        "EXISTS_AT_IMPORT",
                        "A student with this ID No. was added after the preview; skipped.",
                    )
                    outcomes.append(
                        (row["id"], ImportRowOutcome.SKIPPED, None, [*row["messages"], note])
                    )
            for row in rows:
                if row["status"] not in IMPORTABLE_STATUSES:
                    outcomes.append((row["id"], ImportRowOutcome.SKIPPED, None, row["messages"]))
            jobs.set_outcomes([(r, o.value, s, m) for r, o, s, m in outcomes])

            counts = Counter(r["status"] for r in rows)
            result = {
                "imported": imported,
                "skipped_existing": counts[ImportRowStatus.EXISTS] + skipped_late_duplicates,
                "skipped_duplicates": counts[ImportRowStatus.DUPLICATE],
                "skipped_errors": len(error_rows),
                "courses_created": created,
            }
            updated = jobs.update_fields(
                job_id,
                {
                    "status": ImportJobStatus.COMPLETED,
                    "error_policy": payload.error_policy,
                    "confirmed_by": actor.user_id,
                    "confirmed_at": datetime.now(UTC),
                    "summary": {**job["summary"], "result": result},
                },
            )
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="import.completed",
                entity_type="import_job",
                entity_id=job_id,
                after=result,
            )
        return ImportJob.model_validate(updated)

    @staticmethod
    def _resolve_courses(
        conn: DbConnection,
        actor: CurrentUser,
        importable: list[Row],
        payload: ImportConfirmRequest,
    ) -> tuple[dict[str, UUID], list[str]]:
        courses = CourseRepository(conn)
        for course_id in set(payload.course_mapping.values()):
            if courses.get_by_id(course_id) is None:
                raise NotFoundError(
                    f"Mapped course {course_id} was not found.", code="COURSE_NOT_FOUND"
                )
        mapping = {course_key(text): cid for text, cid in payload.course_mapping.items()}
        if payload.create_missing_courses:
            # Serialise auto-creation across concurrent confirms; the lookup below is built
            # after the lock, so it sees courses another import has just created.
            advisory_xact_lock(conn, "courses:auto-create")
        lookup = build_course_lookup(courses.all())  # courses may have been added since preview
        resolved: dict[str, UUID] = {}
        created: list[str] = []
        unresolved: set[str] = set()
        for row in importable:
            text = row["normalized"]["course"]
            if not text or course_key(text) in resolved:
                continue
            key = course_key(text)
            found = mapping.get(key) or lookup(text)
            if found is not None:
                resolved[key] = found
            elif payload.create_missing_courses:
                code = derive_course_code(text, courses.code_exists)
                with translate_constraint_errors(_COURSE_CONFLICTS):
                    course = courses.insert({"code": code, "name": text})
                record_audit(
                    conn,
                    actor_id=actor.user_id,
                    action="course.created",
                    entity_type="course",
                    entity_id=course["id"],
                    after=course,
                )
                resolved[key] = course["id"]
                created.append(text)
            else:
                unresolved.add(text)
        if unresolved:
            raise InvalidCSVError(
                "Some courses in the file are not mapped to an existing course.",
                code="UNMAPPED_COURSES",
                details={"unmapped_courses": sorted(unresolved)},
            )
        return resolved, created
