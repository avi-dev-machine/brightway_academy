from uuid import UUID

from fastapi import APIRouter, status

from app.dependencies import AdminUser, ContainerDep, StaffUser, batch_service
from app.models.batch import Batch
from app.models.student import Student
from app.schemas.batch import BatchAssignmentResult, BatchCreate, BatchStudentsRequest, BatchUpdate
from app.schemas.common import ApiResponse, MessageOut, ok
from app.utils.pagination import PageDep, paged

router = APIRouter()


@router.get("", response_model=ApiResponse[list[Batch]])
def list_batches(
    user: StaffUser,
    container: ContainerDep,
    params: PageDep,
    course_id: UUID | None = None,
    teacher_id: UUID | None = None,
    active: bool | None = None,
) -> ApiResponse[list[Batch]]:
    return paged(
        batch_service(container).search(
            user, course_id=course_id, teacher_id=teacher_id, active=active, params=params
        )
    )


@router.post("", response_model=ApiResponse[Batch], status_code=status.HTTP_201_CREATED)
def create_batch(
    payload: BatchCreate, user: AdminUser, container: ContainerDep
) -> ApiResponse[Batch]:
    return ok(batch_service(container).create(user, payload))


@router.get("/{batch_id}", response_model=ApiResponse[Batch])
def get_batch(batch_id: UUID, user: StaffUser, container: ContainerDep) -> ApiResponse[Batch]:
    return ok(batch_service(container).get(user, batch_id))


@router.patch("/{batch_id}", response_model=ApiResponse[Batch])
def update_batch(
    batch_id: UUID, payload: BatchUpdate, user: AdminUser, container: ContainerDep
) -> ApiResponse[Batch]:
    return ok(batch_service(container).update(user, batch_id, payload))


@router.get("/{batch_id}/students", response_model=ApiResponse[list[Student]])
def list_batch_students(
    batch_id: UUID, user: StaffUser, container: ContainerDep
) -> ApiResponse[list[Student]]:
    return ok(batch_service(container).list_students(user, batch_id))


@router.post("/{batch_id}/students", response_model=ApiResponse[BatchAssignmentResult])
def add_batch_students(
    batch_id: UUID, payload: BatchStudentsRequest, user: AdminUser, container: ContainerDep
) -> ApiResponse[BatchAssignmentResult]:
    return ok(batch_service(container).add_students(user, batch_id, payload.student_ids))


@router.delete("/{batch_id}/students/{student_id}", response_model=ApiResponse[MessageOut])
def remove_batch_student(
    batch_id: UUID, student_id: UUID, user: AdminUser, container: ContainerDep
) -> ApiResponse[MessageOut]:
    batch_service(container).remove_student(user, batch_id, student_id)
    return ok(MessageOut(message="Student removed from the batch."))
