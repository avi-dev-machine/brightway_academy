from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ImportJobStatus(StrEnum):
    PREVIEWED = "PREVIEWED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ImportRowStatus(StrEnum):
    VALID = "VALID"  # importable, no issues
    WARNING = "WARNING"  # importable, with non-blocking issues (e.g. invalid phone kept as-is)
    ERROR = "ERROR"  # not importable until fixed
    DUPLICATE = "DUPLICATE"  # identical repeat of an earlier row in the same file
    EXISTS = "EXISTS"  # ID No. already in the database; never overwritten


IMPORTABLE_STATUSES = (ImportRowStatus.VALID, ImportRowStatus.WARNING)


class ImportErrorPolicy(StrEnum):
    STRICT = "STRICT"  # refuse to import while any row has errors
    SKIP_ERRORS = "SKIP_ERRORS"  # import good rows; error rows are recorded as SKIPPED


class ImportRowOutcome(StrEnum):
    IMPORTED = "IMPORTED"
    SKIPPED = "SKIPPED"


class ImportJob(BaseModel):
    id: UUID
    filename: str
    file_sha256: str
    status: ImportJobStatus
    total_rows: int
    summary: dict[str, Any]
    error_policy: ImportErrorPolicy | None
    created_by: UUID | None
    confirmed_by: UUID | None
    confirmed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ImportRow(BaseModel):
    id: UUID
    job_id: UUID
    row_number: int
    raw: dict[str, Any]
    normalized: dict[str, Any] | None
    status: ImportRowStatus
    messages: list[dict[str, Any]]
    outcome: ImportRowOutcome | None
    student_id: UUID | None
