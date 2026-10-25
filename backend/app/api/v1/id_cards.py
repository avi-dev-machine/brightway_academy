from typing import Any
from uuid import UUID

from fastapi import APIRouter, status
from fastapi.responses import Response

from app.dependencies import AdminUser, ContainerDep, CurrentUserDep, id_card_service
from app.models.id_card import IdCard, IdCardTemplate
from app.schemas.common import ApiResponse, ok
from app.schemas.id_card import GenerateIdCardRequest, TemplateCreate, TemplateUpdate

router = APIRouter()

_PDF: dict[int | str, dict[str, Any]] = {200: {"content": {"application/pdf": {}}}}


def _pdf(data: bytes, filename: str, *, inline: bool = False) -> Response:
    disposition = "inline" if inline else "attachment"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/templates", response_model=ApiResponse[list[IdCardTemplate]])
def list_templates(user: AdminUser, container: ContainerDep) -> ApiResponse[list[IdCardTemplate]]:
    return ok(id_card_service(container).list_templates())


@router.post(
    "/templates", response_model=ApiResponse[IdCardTemplate], status_code=status.HTTP_201_CREATED
)
def create_template(
    payload: TemplateCreate, user: AdminUser, container: ContainerDep
) -> ApiResponse[IdCardTemplate]:
    return ok(id_card_service(container).create_template(user, payload))


@router.patch("/templates/{template_id}", response_model=ApiResponse[IdCardTemplate])
def update_template(
    template_id: UUID, payload: TemplateUpdate, user: AdminUser, container: ContainerDep
) -> ApiResponse[IdCardTemplate]:
    return ok(id_card_service(container).update_template(user, template_id, payload))


@router.get("/templates/{template_id}/preview", response_class=Response, responses=_PDF)
def preview_template(template_id: UUID, user: AdminUser, container: ContainerDep) -> Response:
    """Render the template with sample data."""
    return _pdf(
        id_card_service(container).preview_template(template_id), "preview.pdf", inline=True
    )


@router.post(
    "/students/{student_id}/generate",
    response_model=ApiResponse[IdCard],
    status_code=status.HTTP_201_CREATED,
)
def generate_id_card(
    student_id: UUID,
    user: AdminUser,
    container: ContainerDep,
    payload: GenerateIdCardRequest | None = None,
) -> ApiResponse[IdCard]:
    """Generate (or regenerate) a student's ID card. Previous cards are kept in history."""
    template_id = payload.template_id if payload else None
    return ok(id_card_service(container).generate(user, student_id, template_id))


@router.get("/students/{student_id}/download", response_class=Response, responses=_PDF)
def download_id_card(student_id: UUID, user: CurrentUserDep, container: ContainerDep) -> Response:
    data = id_card_service(container).download_latest(user, student_id)
    return _pdf(data, f"id-card-{student_id}.pdf")


@router.get("/students/{student_id}/history", response_model=ApiResponse[list[IdCard]])
def id_card_history(
    student_id: UUID, user: AdminUser, container: ContainerDep
) -> ApiResponse[list[IdCard]]:
    return ok(id_card_service(container).history(student_id))
