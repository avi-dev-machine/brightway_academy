from uuid import UUID

from pydantic import BaseModel, Field

from app.models.import_job import ImportErrorPolicy, ImportJob, ImportRow


class ImportConfirmRequest(BaseModel):
    error_policy: ImportErrorPolicy = ImportErrorPolicy.STRICT
    course_mapping: dict[str, UUID] = Field(
        default_factory=dict,
        description="Map a course name exactly as written in the CSV to an existing course id.",
    )
    create_missing_courses: bool = False


class ImportPreview(BaseModel):
    job: ImportJob
    problem_rows: list[ImportRow] = Field(
        description="Up to 50 rows that are not VALID; use the rows endpoint for all of them."
    )
