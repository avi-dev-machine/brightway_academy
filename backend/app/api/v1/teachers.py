from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.dependencies import AdminUser, ContainerDep, CurrentUserDep, teacher_service
from app.models.teacher import Teacher
from app.schemas.common import ApiResponse, ok
from app.schemas.teacher import TeacherCreate, TeacherUpdate
from app.utils.pagination import PageDep, paged

router = APIRouter()


@router.get("", response_model=ApiResponse[list[Teacher]])
def list_teachers(
    user: AdminUser,
    container: ContainerDep,
    params: PageDep,
    active: bool | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> ApiResponse[list[Teacher]]:
    return paged(teacher_service(container).search(active=active, q=q, params=params))


@router.post("", response_model=ApiResponse[Teacher], status_code=status.HTTP_201_CREATED)
def create_teacher(
    payload: TeacherCreate, user: AdminUser, container: ContainerDep
) -> ApiResponse[Teacher]:
    return ok(teacher_service(container).create(user, payload))


@router.get("/me", response_model=ApiResponse[Teacher])
def get_my_profile(user: CurrentUserDep, container: ContainerDep) -> ApiResponse[Teacher]:
    return ok(teacher_service(container).get_own(user))


@router.get("/{teacher_id}", response_model=ApiResponse[Teacher])
def get_teacher(teacher_id: UUID, user: AdminUser, container: ContainerDep) -> ApiResponse[Teacher]:
    return ok(teacher_service(container).get(teacher_id))


@router.patch("/{teacher_id}", response_model=ApiResponse[Teacher])
def update_teacher(
    teacher_id: UUID, payload: TeacherUpdate, user: AdminUser, container: ContainerDep
) -> ApiResponse[Teacher]:
    return ok(teacher_service(container).update(user, teacher_id, payload))
