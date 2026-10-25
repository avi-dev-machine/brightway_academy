from datetime import date, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import Response

from app.dependencies import AdminUser, ContainerDep, report_service
from app.schemas.common import ApiResponse, ok
from app.schemas.report import CollectionReport, DashboardStats, OutstandingRow
from app.utils.dates import local_today
from app.utils.pagination import PageDep, paged

router = APIRouter()

_CSV: dict[int | str, dict[str, Any]] = {200: {"content": {"text/csv": {}}}}


def _csv(data: bytes, filename: str) -> Response:
    return Response(
        content=data,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )


def _range(
    container: ContainerDep, date_from: date | None, date_to: date | None
) -> tuple[date, date]:
    end = date_to or local_today(container.settings.timezone)
    return date_from or end.replace(day=1), end


@router.get("/dashboard", response_model=ApiResponse[DashboardStats])
def dashboard(user: AdminUser, container: ContainerDep) -> ApiResponse[DashboardStats]:
    return ok(report_service(container).dashboard())


@router.get("/fees/collections", response_model=ApiResponse[CollectionReport])
def fee_collections(
    user: AdminUser,
    container: ContainerDep,
    date_from: date | None = None,
    date_to: date | None = None,
) -> ApiResponse[CollectionReport]:
    start, end = _range(container, date_from, date_to)
    return ok(report_service(container).collections(start, end))


@router.get("/fees/outstanding", response_model=ApiResponse[list[OutstandingRow]])
def outstanding_fees(
    user: AdminUser, container: ContainerDep, params: PageDep, course_id: UUID | None = None
) -> ApiResponse[list[OutstandingRow]]:
    return paged(report_service(container).outstanding(course_id=course_id, params=params))


@router.get("/exports/students.csv", response_class=Response, responses=_CSV)
def export_students(user: AdminUser, container: ContainerDep) -> Response:
    return _csv(report_service(container).export_students(), "students.csv")


@router.get("/exports/fees.csv", response_class=Response, responses=_CSV)
def export_fees(user: AdminUser, container: ContainerDep) -> Response:
    return _csv(report_service(container).export_fees(), "fees.csv")


@router.get("/exports/payments.csv", response_class=Response, responses=_CSV)
def export_payments(
    user: AdminUser,
    container: ContainerDep,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Response:
    end = date_to or local_today(container.settings.timezone)
    start = date_from or end - timedelta(days=30)
    return _csv(report_service(container).export_payments(start, end), "payments.csv")
