from uuid import UUID

from fastapi import APIRouter, status

from app.dependencies import AdminUser, ContainerDep, CurrentUserDep, fee_service, payment_service
from app.models.fee import Fee, FeePlan, FeeStatus
from app.schemas.common import ApiResponse, ok
from app.schemas.fee import (
    AssignPlanRequest,
    CancelFeeRequest,
    ConcessionRequest,
    FeeCreate,
    FeePlanCreate,
    FeePlanUpdate,
    FeeSummary,
)
from app.schemas.payment import OfflinePaymentRequest, PaymentResult, StudentUpiPaymentRequest
from app.utils.pagination import PageDep, paged

router = APIRouter()


# ---------------------------------------------------------------------- fee plans
@router.get("/plans", response_model=ApiResponse[list[FeePlan]])
def list_plans(
    user: AdminUser,
    container: ContainerDep,
    active: bool | None = None,
    course_id: UUID | None = None,
) -> ApiResponse[list[FeePlan]]:
    return ok(fee_service(container).list_plans(active=active, course_id=course_id))


@router.post("/plans", response_model=ApiResponse[FeePlan], status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: FeePlanCreate, user: AdminUser, container: ContainerDep
) -> ApiResponse[FeePlan]:
    return ok(fee_service(container).create_plan(user, payload))


@router.patch("/plans/{plan_id}", response_model=ApiResponse[FeePlan])
def update_plan(
    plan_id: UUID, payload: FeePlanUpdate, user: AdminUser, container: ContainerDep
) -> ApiResponse[FeePlan]:
    return ok(fee_service(container).update_plan(user, plan_id, payload))


# ---------------------------------------------------------------------- student fees
@router.post(
    "/students/{student_id}/assign-plan",
    response_model=ApiResponse[list[Fee]],
    status_code=status.HTTP_201_CREATED,
)
def assign_plan(
    student_id: UUID, payload: AssignPlanRequest, user: AdminUser, container: ContainerDep
) -> ApiResponse[list[Fee]]:
    return ok(fee_service(container).assign_plan(user, student_id, payload))


@router.get("/students/{student_id}/summary", response_model=ApiResponse[FeeSummary])
def student_fee_summary(
    student_id: UUID, user: CurrentUserDep, container: ContainerDep
) -> ApiResponse[FeeSummary]:
    return ok(fee_service(container).summary(user, student_id))


@router.get("", response_model=ApiResponse[list[Fee]])
def list_fees(
    user: CurrentUserDep,
    container: ContainerDep,
    params: PageDep,
    student_id: UUID | None = None,
    status: FeeStatus | None = None,
) -> ApiResponse[list[Fee]]:
    """Admins see all fees; students only their own."""
    return paged(
        fee_service(container).list_fees(user, student_id=student_id, status=status, params=params)
    )


@router.post("", response_model=ApiResponse[Fee], status_code=status.HTTP_201_CREATED)
def create_fee(payload: FeeCreate, user: AdminUser, container: ContainerDep) -> ApiResponse[Fee]:
    return ok(fee_service(container).create_fee(user, payload))


@router.get("/{fee_id}", response_model=ApiResponse[Fee])
def get_fee(fee_id: UUID, user: CurrentUserDep, container: ContainerDep) -> ApiResponse[Fee]:
    return ok(fee_service(container).get_fee(user, fee_id))


@router.post("/{fee_id}/concessions", response_model=ApiResponse[Fee])
def apply_concession(
    fee_id: UUID, payload: ConcessionRequest, user: AdminUser, container: ContainerDep
) -> ApiResponse[Fee]:
    return ok(fee_service(container).apply_concession(user, fee_id, payload))


@router.post("/{fee_id}/cancel", response_model=ApiResponse[Fee])
def cancel_fee(
    fee_id: UUID, payload: CancelFeeRequest, user: AdminUser, container: ContainerDep
) -> ApiResponse[Fee]:
    return ok(fee_service(container).cancel_fee(user, fee_id, payload))


@router.post(
    "/{fee_id}/offline-payments",
    response_model=ApiResponse[PaymentResult],
    status_code=status.HTTP_201_CREATED,
)
def record_offline_payment(
    fee_id: UUID, payload: OfflinePaymentRequest, user: AdminUser, container: ContainerDep
) -> ApiResponse[PaymentResult]:
    """Record a cash/UPI/cheque payment received at the academy; issues a receipt."""
    return ok(payment_service(container).record_offline_payment(user, fee_id, payload))


@router.post(
    "/{fee_id}/upi-payments",
    response_model=ApiResponse[PaymentResult],
    status_code=status.HTTP_201_CREATED,
)
def record_student_upi_payment(
    fee_id: UUID, payload: StudentUpiPaymentRequest, user: CurrentUserDep, container: ContainerDep
) -> ApiResponse[PaymentResult]:
    """Record a direct UPI payment submitted by the student with UPI reference."""
    return ok(payment_service(container).record_student_upi_payment(user, fee_id, payload))
