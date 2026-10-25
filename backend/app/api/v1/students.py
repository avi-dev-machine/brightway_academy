from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile, status
from fastapi.responses import Response

from app.dependencies import (
    AdminUser,
    ContainerDep,
    CurrentUserDep,
    StaffUser,
    notification_service,
    student_service,
)
from app.models.student import Student, StudentMonthlyFee, StudentStatus
from app.schemas.common import ApiResponse, ok
from app.schemas.student import (
    BroadcastDueNoticeRequest,
    BroadcastDueNoticeResult,
    DueFeeNoticeResult,
    StudentCreate,
    StudentPhotoResult,
    StudentUpdate,
)
from app.utils.file_validation import read_upload_limited
from app.utils.pagination import PageDep, paged

router = APIRouter()


@router.get("", response_model=ApiResponse[list[Student]])
def list_students(
    user: StaffUser,
    container: ContainerDep,
    params: PageDep,
    q: Annotated[
        str | None, Query(max_length=100, description="Name, ID No., contact or guardian")
    ] = None,
    course_id: UUID | None = None,
    batch_id: UUID | None = None,
    status: StudentStatus | None = None,
    program: str | None = None,
    has_id: bool | None = None,
    fee_status: str | None = None,
) -> ApiResponse[list[Student]]:
    return paged(
        student_service(container).search(
            user,
            q=q,
            course_id=course_id,
            batch_id=batch_id,
            status=status,
            program=program,
            has_id=has_id,
            fee_status=fee_status,
            params=params,
        )
    )


@router.post("", response_model=ApiResponse[Student], status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate, user: AdminUser, container: ContainerDep
) -> ApiResponse[Student]:
    return ok(student_service(container).create(user, payload))


@router.get("/me", response_model=ApiResponse[Student])
def get_my_record(user: CurrentUserDep, container: ContainerDep) -> ApiResponse[Student]:
    return ok(student_service(container).get_own(user))


@router.post("/notify-all-unpaid", response_model=ApiResponse[BroadcastDueNoticeResult])
def notify_all_unpaid_students(
    user: AdminUser,
    container: ContainerDep,
    payload: BroadcastDueNoticeRequest | None = None,
) -> ApiResponse[BroadcastDueNoticeResult]:
    p = payload or BroadcastDueNoticeRequest()
    return ok(
        student_service(container).notify_all_unpaid(
            user,
            notification_service(container),
            program=p.program,
            course_id=p.course_id,
            custom_note=p.custom_note,
        )
    )


@router.get("/{student_id}", response_model=ApiResponse[Student])
def get_student(
    student_id: UUID, user: CurrentUserDep, container: ContainerDep
) -> ApiResponse[Student]:
    return ok(student_service(container).get(user, student_id))


@router.get("/{student_id}/monthly-fees", response_model=ApiResponse[list[StudentMonthlyFee]])
def get_student_monthly_fees(
    student_id: UUID, user: CurrentUserDep, container: ContainerDep
) -> ApiResponse[list[StudentMonthlyFee]]:
    return ok(student_service(container).get_monthly_fees(user, student_id))


@router.post("/{student_id}/notify-due-fee", response_model=ApiResponse[DueFeeNoticeResult])
def notify_student_due_fee(
    student_id: UUID,
    user: AdminUser,
    container: ContainerDep,
    custom_note: str | None = None,
) -> ApiResponse[DueFeeNoticeResult]:
    return ok(
        student_service(container).notify_due_fee(
            user,
            student_id,
            notification_service(container),
            custom_note=custom_note,
        )
    )


@router.patch("/{student_id}", response_model=ApiResponse[Student])
def update_student(
    student_id: UUID, payload: StudentUpdate, user: AdminUser, container: ContainerDep
) -> ApiResponse[Student]:
    return ok(student_service(container).update(user, student_id, payload))


@router.post("/{student_id}/deactivate", response_model=ApiResponse[Student])
def deactivate_student(
    student_id: UUID, user: AdminUser, container: ContainerDep
) -> ApiResponse[Student]:
    """Students are never hard-deleted; payments and receipts stay intact."""
    return ok(student_service(container).set_status(user, student_id, StudentStatus.INACTIVE))


@router.post("/{student_id}/activate", response_model=ApiResponse[Student])
def activate_student(
    student_id: UUID, user: AdminUser, container: ContainerDep
) -> ApiResponse[Student]:
    return ok(student_service(container).set_status(user, student_id, StudentStatus.ACTIVE))


@router.put("/{student_id}/photo", response_model=ApiResponse[StudentPhotoResult])
def upload_photo(
    student_id: UUID,
    user: AdminUser,
    container: ContainerDep,
    photo: Annotated[UploadFile, File(description="JPEG, PNG or WebP, max 5 MB")],
) -> ApiResponse[StudentPhotoResult]:
    """Validate and store the photo, then regenerate the student's ID card."""
    data = read_upload_limited(photo.file, container.settings.max_photo_bytes)
    return ok(
        student_service(container).upload_photo(
            user, student_id, data=data, filename=photo.filename, content_type=photo.content_type
        )
    )


@router.get(
    "/{student_id}/photo",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}},
)
def get_photo(student_id: UUID, user: CurrentUserDep, container: ContainerDep) -> Response:
    data = student_service(container).get_photo(user, student_id)
    return Response(
        content=data, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"}
    )
