from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Request, status
from starlette.concurrency import run_in_threadpool

from app.dependencies import ContainerDep, CurrentUserDep, payment_service
from app.exceptions import ValidationFailedError
from app.models.payment import Payment, PaymentStatus
from app.schemas.common import ApiResponse, ok
from app.schemas.payment import (
    IDEMPOTENCY_KEY_PATTERN,
    CheckoutOrder,
    CreateOrderRequest,
    PaymentConfig,
    PaymentResult,
    VerifyPaymentRequest,
    WebhookResult,
)
from app.utils.pagination import PageDep, paged
from app.utils.rate_limit import client_ip

router = APIRouter()

MAX_WEBHOOK_BYTES = 256 * 1024


@router.get("/config", response_model=ApiResponse[PaymentConfig])
def checkout_config(user: CurrentUserDep, container: ContainerDep) -> ApiResponse[PaymentConfig]:
    """Public checkout key for the frontend. Secrets are never returned."""
    return ok(payment_service(container).config())


@router.post(
    "/orders", response_model=ApiResponse[CheckoutOrder], status_code=status.HTTP_201_CREATED
)
def create_order(
    payload: CreateOrderRequest,
    user: CurrentUserDep,
    container: ContainerDep,
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key", pattern=IDEMPOTENCY_KEY_PATTERN)
    ] = None,
) -> ApiResponse[CheckoutOrder]:
    """Create (or reuse) a provider order. The amount is computed server-side from the fee."""
    return ok(payment_service(container).create_order(user, payload, idempotency_key))


@router.post("/verify", response_model=ApiResponse[PaymentResult])
def verify_payment(
    payload: VerifyPaymentRequest, user: CurrentUserDep, container: ContainerDep
) -> ApiResponse[PaymentResult]:
    """Verify the Checkout signature and confirm the payment with the provider."""
    return ok(payment_service(container).verify_checkout(user, payload))


@router.post("/webhooks/razorpay", response_model=ApiResponse[WebhookResult])
async def razorpay_webhook(request: Request, container: ContainerDep) -> ApiResponse[WebhookResult]:
    """Unauthenticated by design; trust comes only from the HMAC signature."""
    container.webhook_limiter.hit(f"razorpay:{client_ip(request)}")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_WEBHOOK_BYTES:
            raise ValidationFailedError("Webhook payload is too large.", code="PAYLOAD_TOO_LARGE")
    result = await run_in_threadpool(
        payment_service(container).handle_webhook,
        bytes(body),
        request.headers.get("x-razorpay-signature"),
        request.headers.get("x-razorpay-event-id"),
    )
    return ok(result)


@router.get("", response_model=ApiResponse[list[Payment]])
def list_payments(
    user: CurrentUserDep,
    container: ContainerDep,
    params: PageDep,
    student_id: UUID | None = None,
    fee_id: UUID | None = None,
    status: PaymentStatus | None = None,
) -> ApiResponse[list[Payment]]:
    return paged(
        payment_service(container).search(
            user, student_id=student_id, fee_id=fee_id, status=status, params=params
        )
    )


@router.get("/{payment_id}", response_model=ApiResponse[Payment])
def get_payment(
    payment_id: UUID, user: CurrentUserDep, container: ContainerDep
) -> ApiResponse[Payment]:
    return ok(payment_service(container).get(user, payment_id))
