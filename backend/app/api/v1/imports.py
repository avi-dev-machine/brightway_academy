from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, UploadFile, status

from app.dependencies import AdminUser, ContainerDep, csv_import_service
from app.models.import_job import ImportJob, ImportRow, ImportRowStatus
from app.schemas.common import ApiResponse, ok
from app.schemas.import_job import ImportConfirmRequest, ImportPreview
from app.utils.file_validation import read_upload_limited
from app.utils.pagination import PageDep, paged

router = APIRouter()


@router.post(
    "/students/preview",
    response_model=ApiResponse[ImportPreview],
    status_code=status.HTTP_201_CREATED,
)
def preview_student_import(
    user: AdminUser,
    container: ContainerDep,
    file: Annotated[UploadFile, File(description="Legacy student CSV")],
) -> ApiResponse[ImportPreview]:
    """Validate the CSV and store a preview. Nothing is imported until confirmed."""
    data = read_upload_limited(file.file, container.settings.max_csv_bytes)
    return ok(
        csv_import_service(container).preview(
            user, filename=file.filename, content_type=file.content_type, data=data
        )
    )


@router.get("", response_model=ApiResponse[list[ImportJob]])
def list_import_jobs(
    user: AdminUser, container: ContainerDep, params: PageDep
) -> ApiResponse[list[ImportJob]]:
    return paged(csv_import_service(container).list_jobs(params))


@router.get("/{job_id}", response_model=ApiResponse[ImportJob])
def get_import_job(
    job_id: UUID, user: AdminUser, container: ContainerDep
) -> ApiResponse[ImportJob]:
    return ok(csv_import_service(container).get_job(job_id))


@router.get("/{job_id}/rows", response_model=ApiResponse[list[ImportRow]])
def list_import_rows(
    job_id: UUID,
    user: AdminUser,
    container: ContainerDep,
    params: PageDep,
    status: ImportRowStatus | None = None,
) -> ApiResponse[list[ImportRow]]:
    return paged(csv_import_service(container).list_rows(job_id, status=status, params=params))


@router.post("/{job_id}/confirm", response_model=ApiResponse[ImportJob])
def confirm_import(
    job_id: UUID, payload: ImportConfirmRequest, user: AdminUser, container: ContainerDep
) -> ApiResponse[ImportJob]:
    """Import the previewed rows in a single transaction. Confirming again is a no-op."""
    return ok(csv_import_service(container).confirm(user, job_id, payload))
