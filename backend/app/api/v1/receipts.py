from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import Response

from app.dependencies import ContainerDep, CurrentUserDep, receipt_service
from app.models.receipt import Receipt
from app.schemas.common import ApiResponse, ok
from app.utils.pagination import PageDep, paged

router = APIRouter()


@router.get("", response_model=ApiResponse[list[Receipt]])
def list_receipts(
    user: CurrentUserDep, container: ContainerDep, params: PageDep, student_id: UUID | None = None
) -> ApiResponse[list[Receipt]]:
    return paged(receipt_service(container).search(user, student_id=student_id, params=params))


@router.get("/{receipt_id}", response_model=ApiResponse[Receipt])
def get_receipt(
    receipt_id: UUID, user: CurrentUserDep, container: ContainerDep
) -> ApiResponse[Receipt]:
    return ok(receipt_service(container).get(user, receipt_id))


@router.get(
    "/{receipt_id}/download",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
def download_receipt(receipt_id: UUID, user: CurrentUserDep, container: ContainerDep) -> Response:
    filename, data = receipt_service(container).download(user, receipt_id)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )
