from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.dependencies import AdminUser, ContainerDep, CurrentUserDep, course_service
from app.models.course import Course
from app.schemas.common import ApiResponse, ok
from app.schemas.course import CourseCreate, CourseUpdate
from app.utils.pagination import PageDep, paged

router = APIRouter()


@router.get("", response_model=ApiResponse[list[Course]])
def list_courses(
    user: CurrentUserDep,
    container: ContainerDep,
    params: PageDep,
    active: bool | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
) -> ApiResponse[list[Course]]:
    return paged(course_service(container).search(active=active, q=q, params=params))


@router.post("", response_model=ApiResponse[Course], status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate, user: AdminUser, container: ContainerDep
) -> ApiResponse[Course]:
    return ok(course_service(container).create(user, payload))


@router.get("/{course_id}", response_model=ApiResponse[Course])
def get_course(
    course_id: UUID, user: CurrentUserDep, container: ContainerDep
) -> ApiResponse[Course]:
    return ok(course_service(container).get(course_id))


@router.patch("/{course_id}", response_model=ApiResponse[Course])
def update_course(
    course_id: UUID, payload: CourseUpdate, user: AdminUser, container: ContainerDep
) -> ApiResponse[Course]:
    return ok(course_service(container).update(user, course_id, payload))
