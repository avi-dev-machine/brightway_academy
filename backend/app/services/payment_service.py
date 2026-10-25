"""Payment domain: orders, verification, webhooks, offline payments and refunds.

Independent of Razorpay: it talks to a PaymentProvider. Every settlement runs in one
database transaction with the payment row locked (SELECT ... FOR UPDATE), so a payment
can never be applied twice, whatever mix of checkout callbacks and duplicate webhooks
arrives.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from enum import StrEnum
from uuid import UUID
from zoneinfo import ZoneInfo

from app.core.constants import CURRENCY, MIN_ONLINE_PAYMENT_PAISE
from app.core.permissions import CurrentUser
from app.db.client import Database, DbConnection
from app.exceptions import (
    AppError,
    ConflictError,
    ExternalServiceError,
    ForbiddenError,
    InvalidStateError,
    NotFoundError,
    PaymentVerificationError,
    ValidationFailedError,
)
from app.integrations.payments import (
    PaymentProvider,
    ProviderPayment,
    ProviderRefund,
    ProviderWebhookEvent,
)
from app.models.fee import FeeStatus, compute_fee_status, outstanding
from app.models.payment import (
    Payment,
    PaymentProviderName,
    PaymentStatus,
    can_transition,
    ensure_transition,
)
from app.models.receipt import Receipt
from app.repositories.base import Row
from app.repositories.fee_repository import FeeRepository
from app.repositories.payment_repository import PaymentEventRepository, PaymentRepository
from app.repositories.receipt_repository import ReceiptRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.payment import (
    CheckoutOrder,
    CreateOrderRequest,
    OfflinePaymentRequest,
    PaymentConfig,
    PaymentResult,
    StudentUpiPaymentRequest,
    VerifyPaymentRequest,
    WebhookResult,
)
from app.services.audit_service import record_audit
from app.services.notification_service import NotificationService
from app.services.receipt_service import ReceiptService
from app.utils.dates import local_today
from app.utils.pagination import Page, PageParams

logger = logging.getLogger(__name__)

ORDER_REUSE_WINDOW = timedelta(minutes=30)
_SETTLEMENT_EVENTS = {"payment.captured", "order.paid", "payment.authorized", "payment.failed"}


class Outcome(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    ALREADY_PROCESSED = "ALREADY_PROCESSED"
    PENDING = "PENDING"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    ORDER_MISMATCH = "ORDER_MISMATCH"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    IGNORED = "IGNORED"


_VERIFICATION_FAILURES = {Outcome.AMOUNT_MISMATCH, Outcome.ORDER_MISMATCH}


@dataclass
class Settlement:
    payment: Row
    receipt: Row | None
    outcome: Outcome


def payment_not_found() -> NotFoundError:
    return NotFoundError("Payment was not found.", code="PAYMENT_NOT_FOUND")


class PaymentService:
    def __init__(
        self,
        db: Database,
        provider: PaymentProvider,
        receipts: ReceiptService,
        notifications: NotificationService,
        timezone: str,
    ) -> None:
        self.db = db
        self.provider = provider
        self.receipts = receipts
        self.notifications = notifications
        self.timezone = timezone

    def config(self) -> PaymentConfig:
        return PaymentConfig(
            provider=self.provider.name, key_id=self.provider.checkout_key, currency=CURRENCY
        )

    # ------------------------------------------------------------------ online checkout
    def create_order(
        self, user: CurrentUser, payload: CreateOrderRequest, idempotency_key: str | None
    ) -> CheckoutOrder:
        if not (user.is_admin or user.is_student):
            raise ForbiddenError()
        with self.db.transaction() as conn:
            fee = FeeRepository(conn).get_by_id(payload.fee_id, for_update=True)
            if fee is None:
                raise NotFoundError("Fee was not found.", code="FEE_NOT_FOUND")
            if user.is_student and fee["student_id"] != user.student_id:
                raise ForbiddenError("You can only pay your own fees.")
            payments = PaymentRepository(conn)
            if idempotency_key:
                existing = payments.get_by_idempotency_key(idempotency_key)
                if existing is not None:
                    return self._replay_order(conn, existing, fee, payload)
            amount = self._payable_amount(fee, payload.amount_paise)
            if amount < MIN_ONLINE_PAYMENT_PAISE:
                raise ValidationFailedError(
                    "The minimum online payment is INR 1.00.", code="AMOUNT_TOO_SMALL"
                )
            reusable = payments.find_open_order(
                fee_id=fee["id"],
                amount_paise=amount,
                provider=self.provider.name,
                created_after=datetime.now(UTC) - ORDER_REUSE_WINDOW,
            )
            if reusable is not None:
                return self._checkout(conn, reusable, fee)
            payment = payments.insert(
                {
                    "fee_id": fee["id"],
                    "student_id": fee["student_id"],
                    "amount_paise": amount,
                    "currency": CURRENCY,
                    "provider": self.provider.name,
                    "status": PaymentStatus.CREATED,
                    "idempotency_key": idempotency_key,
                    "created_by": user.user_id,
                }
            )

        # The provider call happens outside the transaction so no row locks are held
        # during network I/O.
        try:
            order = self.provider.create_order(
                amount_paise=amount,
                currency=CURRENCY,
                receipt=payment["id"].hex[:40],
                notes={
                    "payment_id": str(payment["id"]),
                    "fee_id": str(fee["id"]),
                    "student_id": str(fee["student_id"]),
                },
            )
            if order.amount_paise != amount or order.currency != CURRENCY:
                raise ExternalServiceError("The payment provider returned an unexpected order.")
        except AppError:
            with self.db.transaction() as conn:
                PaymentRepository(conn).update_fields(
                    payment["id"],
                    {"status": PaymentStatus.FAILED, "failure_reason": "ORDER_CREATION_FAILED"},
                )
            raise

        with self.db.transaction() as conn:
            updated = PaymentRepository(conn).update_fields(
                payment["id"], {"provider_order_id": order.order_id}
            )
            assert updated is not None
            record_audit(
                conn,
                actor_id=user.user_id,
                action="payment.order_created",
                entity_type="payment",
                entity_id=payment["id"],
                after=updated,
            )
            return self._checkout(conn, updated, fee)

    def verify_checkout(self, user: CurrentUser, payload: VerifyPaymentRequest) -> PaymentResult:
        with self.db.transaction() as conn:
            payment = PaymentRepository(conn).get_by_order_id(payload.provider_order_id)
        if payment is None:
            raise payment_not_found()
        self._ensure_access(user, payment)
        if not self.provider.verify_checkout_signature(
            order_id=payload.provider_order_id,
            payment_id=payload.provider_payment_id,
            signature=payload.signature,
        ):
            with self.db.transaction() as conn:
                record_audit(
                    conn,
                    actor_id=user.user_id,
                    action="payment.signature_rejected",
                    entity_type="payment",
                    entity_id=payment["id"],
                )
            raise PaymentVerificationError(
                "Payment signature is invalid.", code="INVALID_PAYMENT_SIGNATURE"
            )
        # Never trust the browser's success callback alone: confirm with the provider.
        remote = self.provider.fetch_payment(payload.provider_payment_id)
        settlement = self._apply_provider_payment(payment["id"], remote, actor_id=user.user_id)
        return self._result(settlement)

    # ------------------------------------------------------------------ webhooks
    def handle_webhook(
        self, body: bytes, signature: str | None, event_id: str | None
    ) -> WebhookResult:
        if not signature or not self.provider.verify_webhook_signature(body, signature):
            raise PaymentVerificationError(
                "Invalid webhook signature.", code="INVALID_WEBHOOK_SIGNATURE"
            )
        event = self.provider.parse_webhook(body, event_id)
        with self.db.transaction() as conn:
            events = PaymentEventRepository(conn)
            stored = events.insert_if_new(
                provider=self.provider.name,
                event_id=event.event_id,
                event_type=event.event_type,
                payload=event.payload,
            )
            if stored is None:
                stored = events.get(self.provider.name, event.event_id)
                assert stored is not None
                if stored["status"] in ("PROCESSED", "IGNORED"):
                    return WebhookResult(status="duplicate", detail=stored["result"])
        try:
            outcome, detail = self._process_event(event)
        except Exception as exc:
            with self.db.transaction() as conn:
                PaymentEventRepository(conn).mark(
                    stored["id"], status="FAILED", result=type(exc).__name__
                )
            raise
        with self.db.transaction() as conn:
            PaymentEventRepository(conn).mark(
                stored["id"],
                status="IGNORED" if outcome == Outcome.IGNORED else "PROCESSED",
                result=outcome.value,
            )
        return WebhookResult(status=outcome.value.lower(), detail=detail)

    def _process_event(self, event: ProviderWebhookEvent) -> tuple[Outcome, str | None]:
        if event.event_type in _SETTLEMENT_EVENTS:
            if event.payment is None or not event.order_id:
                return Outcome.IGNORED, "event has no payment"
            with self.db.transaction() as conn:
                payment = PaymentRepository(conn).get_by_order_id(event.order_id)
            if payment is None:
                logger.warning("webhook for an unknown order", extra={"order_id": event.order_id})
                return Outcome.IGNORED, "unknown order"
            # The webhook body is signed by the provider, so its payment entity is trusted.
            settlement = self._apply_provider_payment(payment["id"], event.payment, actor_id=None)
            return settlement.outcome, None
        if event.event_type == "refund.processed" and event.refund is not None:
            return self._apply_refund(event.refund), None
        return Outcome.IGNORED, f"unhandled event {event.event_type}"

    # ------------------------------------------------------------------ offline payments
    def record_offline_payment(
        self, actor: CurrentUser, fee_id: UUID, payload: OfflinePaymentRequest
    ) -> PaymentResult:
        today = local_today(self.timezone)
        if payload.paid_on and payload.paid_on > today:
            raise ValidationFailedError("paid_on cannot be in the future.", code="FUTURE_DATE")
        if payload.paid_on is None or payload.paid_on == today:
            paid_at = datetime.now(UTC)
        else:
            paid_at = datetime.combine(payload.paid_on, time(12, 0), tzinfo=ZoneInfo(self.timezone))

        with self.db.transaction() as conn:
            payments = PaymentRepository(conn)
            if payload.idempotency_key:
                existing = payments.get_by_idempotency_key(payload.idempotency_key)
                if existing is not None:
                    if (
                        existing["fee_id"] != fee_id
                        or existing["amount_paise"] != payload.amount_paise
                    ):
                        raise _idempotency_conflict()
                    receipt = ReceiptRepository(conn).get_by_payment(existing["id"])
                    return self._result(Settlement(existing, receipt, Outcome.ALREADY_PROCESSED))
            fee = FeeRepository(conn).get_by_id(fee_id, for_update=True)
            if fee is None:
                raise NotFoundError("Fee was not found.", code="FEE_NOT_FOUND")
            amount = self._payable_amount(fee, payload.amount_paise)
            payment = payments.insert(
                {
                    "fee_id": fee_id,
                    "student_id": fee["student_id"],
                    "amount_paise": amount,
                    "currency": CURRENCY,
                    "provider": PaymentProviderName.OFFLINE,
                    "method": payload.method,
                    "status": PaymentStatus.CREATED,
                    "idempotency_key": payload.idempotency_key,
                    "reference": payload.reference,
                    "notes": payload.notes,
                    "created_by": actor.user_id,
                }
            )
            settlement = self._record_success(
                conn,
                payment,
                amount_paise=amount,
                currency=CURRENCY,
                provider_payment_id=None,
                method=payload.method.value,
                actor_id=actor.user_id,
                paid_at=paid_at,
            )
        self._generate_receipt_pdf(settlement)
        return self._result(settlement)

    def record_student_upi_payment(
        self, actor: CurrentUser, fee_id: UUID, payload: StudentUpiPaymentRequest
    ) -> PaymentResult:
        if actor.is_teacher:
            raise ForbiddenError("Teachers cannot process student fees.")

        with self.db.transaction() as conn:
            payments = PaymentRepository(conn)
            if payload.idempotency_key:
                existing = payments.get_by_idempotency_key(payload.idempotency_key)
                if existing is not None:
                    receipt = ReceiptRepository(conn).get_by_payment(existing["id"])
                    return self._result(Settlement(existing, receipt, Outcome.ALREADY_PROCESSED))

            fee = FeeRepository(conn).get_by_id(fee_id, for_update=True)
            if fee is None:
                raise NotFoundError("Fee was not found.", code="FEE_NOT_FOUND")

            if actor.is_student and fee["student_id"] != actor.student_id:
                raise ForbiddenError("You can only pay for your own fees.")

            amount = fee["balance_paise"]
            if amount <= 0:
                raise ValidationFailedError("This fee has already been settled.", code="FEE_ALREADY_PAID")

            payment = payments.insert(
                {
                    "fee_id": fee_id,
                    "student_id": fee["student_id"],
                    "amount_paise": amount,
                    "currency": CURRENCY,
                    "provider": PaymentProviderName.OFFLINE,
                    "method": "UPI",
                    "status": PaymentStatus.CREATED,
                    "idempotency_key": payload.idempotency_key,
                    "reference": payload.reference or f"UPI-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
                    "notes": payload.notes or "Paid via Direct UPI / Dynamic QR Code",
                    "created_by": actor.user_id,
                }
            )
            settlement = self._record_success(
                conn,
                payment,
                amount_paise=amount,
                currency=CURRENCY,
                provider_payment_id=None,
                method="UPI",
                actor_id=actor.user_id,
                paid_at=datetime.now(UTC),
            )
        self._generate_receipt_pdf(settlement)
        return self._result(settlement)

    # ------------------------------------------------------------------ queries
    def search(
        self,
        user: CurrentUser,
        *,
        student_id: UUID | None,
        fee_id: UUID | None,
        status: PaymentStatus | None,
        params: PageParams,
    ) -> Page[Payment]:
        if user.is_teacher:
            raise ForbiddenError()
        if user.is_student:
            if student_id is not None and student_id != user.student_id:
                raise ForbiddenError("You can only view your own payments.")
            student_id = user.student_id
        with self.db.transaction() as conn:
            rows, total = PaymentRepository(conn).search(
                student_id=student_id,
                fee_id=fee_id,
                status=status.value if status else None,
                limit=params.limit,
                offset=params.offset,
            )
        return Page([Payment.model_validate(r) for r in rows], total, params)

    def get(self, user: CurrentUser, payment_id: UUID) -> Payment:
        with self.db.transaction() as conn:
            row = PaymentRepository(conn).get_by_id(payment_id)
        if row is None:
            raise payment_not_found()
        self._ensure_access(user, row)
        return Payment.model_validate(row)

    # ------------------------------------------------------------------ settlement core
    def _apply_provider_payment(
        self, payment_id: UUID, remote: ProviderPayment, *, actor_id: UUID | None
    ) -> Settlement:
        with self.db.transaction() as conn:
            payment = PaymentRepository(conn).get_by_id(payment_id, for_update=True)
            assert payment is not None
            if remote.order_id != payment["provider_order_id"]:
                flagged = self._flag_review(
                    conn,
                    payment,
                    f"ORDER_MISMATCH: provider payment {remote.payment_id} belongs to order "
                    f"{remote.order_id}",
                )
                settlement = Settlement(flagged, None, Outcome.ORDER_MISMATCH)
            elif remote.status == "captured":
                settlement = self._record_success(
                    conn,
                    payment,
                    amount_paise=remote.amount_paise,
                    currency=remote.currency,
                    provider_payment_id=remote.payment_id,
                    method=remote.method,
                    actor_id=actor_id,
                    paid_at=datetime.now(UTC),
                )
            elif remote.status == "authorized":
                settlement = self._record_pending(conn, payment, remote.payment_id)
            elif remote.status == "failed":
                settlement = self._record_failure(
                    conn, payment, remote.error_reason or "PAYMENT_FAILED", remote.payment_id
                )
            else:
                settlement = Settlement(payment, None, Outcome.IGNORED)
        self._generate_receipt_pdf(settlement)
        return settlement

    def _record_success(
        self,
        conn: DbConnection,
        payment: Row,
        *,
        amount_paise: int,
        currency: str,
        provider_payment_id: str | None,
        method: str | None,
        actor_id: UUID | None,
        paid_at: datetime,
    ) -> Settlement:
        """Apply a confirmed payment. The caller holds the payment row lock."""
        receipts = ReceiptRepository(conn)
        if payment["status"] == PaymentStatus.SUCCESS:
            return Settlement(
                payment, receipts.get_by_payment(payment["id"]), Outcome.ALREADY_PROCESSED
            )
        if payment["status"] == PaymentStatus.REFUNDED:
            return Settlement(payment, receipts.get_by_payment(payment["id"]), Outcome.IGNORED)
        if amount_paise != payment["amount_paise"] or currency != payment["currency"]:
            flagged = self._flag_review(
                conn,
                payment,
                f"AMOUNT_MISMATCH: expected {payment['amount_paise']} {payment['currency']}, "
                f"received {amount_paise} {currency}",
                provider_payment_id=provider_payment_id,
            )
            return Settlement(flagged, None, Outcome.AMOUNT_MISMATCH)

        ensure_transition(PaymentStatus(payment["status"]), PaymentStatus.SUCCESS)
        payments = PaymentRepository(conn)
        updated = payments.update_fields(
            payment["id"],
            {
                "status": PaymentStatus.SUCCESS,
                "provider_payment_id": provider_payment_id,
                "method": method or payment["method"],
                "paid_at": paid_at,
                "failure_reason": None,
            },
        )
        assert updated is not None

        fees = FeeRepository(conn)
        fee = fees.get_by_id(payment["fee_id"], for_update=True)
        assert fee is not None
        new_paid = fee["paid_paise"] + payment["amount_paise"]
        updated_fee = fees.update_fields(
            fee["id"],
            {
                "paid_paise": new_paid,
                "status": compute_fee_status(
                    amount_paise=fee["amount_paise"],
                    concession_paise=fee["concession_paise"],
                    paid_paise=new_paid,
                    due_date=fee["due_date"],
                    today=local_today(self.timezone),
                    current=FeeStatus(fee["status"]),
                ),
            },
        )
        assert updated_fee is not None

        # Keep student_monthly_fees in sync when monthly fees are paid
        if updated_fee["status"] in (FeeStatus.PAID, "PAID"):
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update student_monthly_fees
                    set status = 'PAID', paid_on = coalesce(paid_on, %s), amount_paise = coalesce(amount_paise, %s)
                    where student_id = %s and period = %s
                    """,
                    (local_today(self.timezone), payment["amount_paise"], fee["student_id"], fee["due_date"]),
                )

        review_reason = None
        if fee["status"] == FeeStatus.CANCELLED:
            review_reason = "FEE_CANCELLED: payment received for a cancelled fee"
        elif outstanding(fee["amount_paise"], fee["concession_paise"], new_paid) < 0:
            review_reason = "OVERPAYMENT: payment exceeds the outstanding balance"
        if review_reason:
            logger.warning(
                "payment flagged for review",
                extra={"payment_id": str(payment["id"]), "reason": review_reason},
            )
            updated = payments.update_fields(
                payment["id"], {"requires_review": True, "review_reason": review_reason}
            )
            assert updated is not None

        receipt = self.receipts.create_record(conn, updated)
        self.notifications.enqueue_payment_success(
            conn, payment=updated, fee=updated_fee, receipt=receipt
        )
        record_audit(
            conn,
            actor_id=actor_id,
            action="payment.succeeded",
            entity_type="payment",
            entity_id=payment["id"],
            before=payment,
            after=updated,
        )
        return Settlement(updated, receipt, Outcome.SUCCEEDED)

    @staticmethod
    def _record_pending(conn: DbConnection, payment: Row, provider_payment_id: str) -> Settlement:
        status = PaymentStatus(payment["status"])
        if status == PaymentStatus.SUCCESS:
            return Settlement(payment, None, Outcome.ALREADY_PROCESSED)
        if not can_transition(status, PaymentStatus.PENDING):
            return Settlement(payment, None, Outcome.PENDING)
        updated = PaymentRepository(conn).update_fields(
            payment["id"],
            {"status": PaymentStatus.PENDING, "provider_payment_id": provider_payment_id},
        )
        assert updated is not None
        return Settlement(updated, None, Outcome.PENDING)

    @staticmethod
    def _record_failure(
        conn: DbConnection, payment: Row, reason: str, provider_payment_id: str
    ) -> Settlement:
        status = PaymentStatus(payment["status"])
        if status in (PaymentStatus.SUCCESS, PaymentStatus.REFUNDED):
            # A late failure for an earlier attempt never undoes a successful payment.
            return Settlement(payment, None, Outcome.IGNORED)
        updated = PaymentRepository(conn).update_fields(
            payment["id"],
            {
                "status": PaymentStatus.FAILED,
                "failure_reason": reason[:300],
                "provider_payment_id": provider_payment_id,
            },
        )
        assert updated is not None
        return Settlement(updated, None, Outcome.FAILED)

    def _apply_refund(self, refund: ProviderRefund) -> Outcome:
        with self.db.transaction() as conn:
            payments = PaymentRepository(conn)
            found = payments.get_by_provider_payment_id(refund.payment_id)
            if found is None:
                return Outcome.IGNORED
            payment = payments.get_by_id(found["id"], for_update=True)
            assert payment is not None
            if payment["status"] == PaymentStatus.REFUNDED:
                return Outcome.ALREADY_PROCESSED
            if payment["status"] != PaymentStatus.SUCCESS:
                return Outcome.IGNORED
            if refund.amount_paise != payment["amount_paise"]:
                self._flag_review(
                    conn,
                    payment,
                    f"PARTIAL_REFUND: {refund.amount_paise} of {payment['amount_paise']} refunded",
                )
                return Outcome.REVIEW_REQUIRED
            ensure_transition(PaymentStatus.SUCCESS, PaymentStatus.REFUNDED)
            updated = payments.update_fields(payment["id"], {"status": PaymentStatus.REFUNDED})
            fees = FeeRepository(conn)
            fee = fees.get_by_id(payment["fee_id"], for_update=True)
            assert fee is not None
            new_paid = max(fee["paid_paise"] - payment["amount_paise"], 0)
            fees.update_fields(
                fee["id"],
                {
                    "paid_paise": new_paid,
                    "status": compute_fee_status(
                        amount_paise=fee["amount_paise"],
                        concession_paise=fee["concession_paise"],
                        paid_paise=new_paid,
                        due_date=fee["due_date"],
                        today=local_today(self.timezone),
                        current=FeeStatus(fee["status"]),
                    ),
                },
            )
            record_audit(
                conn,
                actor_id=None,
                action="payment.refunded",
                entity_type="payment",
                entity_id=payment["id"],
                before=payment,
                after=updated,
            )
        return Outcome.REFUNDED

    @staticmethod
    def _flag_review(
        conn: DbConnection, payment: Row, reason: str, *, provider_payment_id: str | None = None
    ) -> Row:
        logger.warning(
            "payment flagged for review", extra={"payment_id": str(payment["id"]), "reason": reason}
        )
        changes: dict[str, object] = {"requires_review": True, "review_reason": reason[:300]}
        if payment["status"] in (PaymentStatus.CREATED, PaymentStatus.FAILED):
            changes["status"] = PaymentStatus.PENDING  # money may have moved; never mark SUCCESS
        if provider_payment_id and not payment["provider_payment_id"]:
            changes["provider_payment_id"] = provider_payment_id
        updated = PaymentRepository(conn).update_fields(payment["id"], changes)
        assert updated is not None
        record_audit(
            conn,
            actor_id=None,
            action="payment.flagged_for_review",
            entity_type="payment",
            entity_id=payment["id"],
            before=payment,
            after=updated,
        )
        return updated

    # ------------------------------------------------------------------ helpers
    def _payable_amount(self, fee: Row, requested: int | None) -> int:
        if fee["status"] == FeeStatus.CANCELLED:
            raise InvalidStateError("This fee has been cancelled.", code="FEE_CANCELLED")
        balance = outstanding(fee["amount_paise"], fee["concession_paise"], fee["paid_paise"])
        if balance <= 0:
            raise InvalidStateError("This fee is already paid.", code="FEE_ALREADY_PAID")
        amount = requested or balance
        if amount > balance:
            raise ValidationFailedError(
                "The amount exceeds the outstanding balance.",
                code="AMOUNT_EXCEEDS_BALANCE",
                details={"balance_paise": balance},
            )
        return amount

    def _checkout(self, conn: DbConnection, payment: Row, fee: Row) -> CheckoutOrder:
        student = StudentRepository(conn).get_by_id(payment["student_id"])
        assert student is not None
        return CheckoutOrder(
            payment_id=payment["id"],
            provider=payment["provider"],
            provider_order_id=payment["provider_order_id"],
            amount_paise=payment["amount_paise"],
            currency=payment["currency"],
            key_id=self.provider.checkout_key,
            fee_title=fee["title"],
            student_name=student["name"],
            contact=student["contact_e164"],
        )

    def _replay_order(
        self, conn: DbConnection, existing: Row, fee: Row, payload: CreateOrderRequest
    ) -> CheckoutOrder:
        if existing["fee_id"] != fee["id"] or (
            payload.amount_paise is not None and payload.amount_paise != existing["amount_paise"]
        ):
            raise _idempotency_conflict()
        if existing["provider_order_id"] is None or existing["status"] != PaymentStatus.CREATED:
            raise ConflictError(
                "This payment request is no longer open. Use a new idempotency key.",
                code="PAYMENT_NOT_OPEN",
            )
        return self._checkout(conn, existing, fee)

    def _generate_receipt_pdf(self, settlement: Settlement) -> None:
        if settlement.outcome != Outcome.SUCCEEDED or settlement.receipt is None:
            return
        try:
            detail = self.receipts.ensure_pdf(settlement.receipt["id"])
            settlement.receipt = {**settlement.receipt, "pdf_path": detail["pdf_path"]}
        except AppError as exc:
            # The receipt record exists; the PDF is regenerated on the next download.
            logger.warning(
                "receipt pdf generation deferred",
                extra={"receipt_id": str(settlement.receipt["id"]), "code": exc.code},
            )

    @staticmethod
    def _result(settlement: Settlement) -> PaymentResult:
        if settlement.outcome in _VERIFICATION_FAILURES:
            raise PaymentVerificationError(
                "Payment details do not match the order. The payment has been flagged for review.",
                code=settlement.outcome.value,
            )
        return PaymentResult(
            payment=Payment.model_validate(settlement.payment),
            receipt=Receipt.model_validate(settlement.receipt) if settlement.receipt else None,
            outcome=settlement.outcome.value,
        )

    @staticmethod
    def _ensure_access(user: CurrentUser, payment: Row) -> None:
        if user.is_admin or (user.is_student and payment["student_id"] == user.student_id):
            return
        raise ForbiddenError("You do not have access to this payment.")


def _idempotency_conflict() -> ConflictError:
    return ConflictError(
        "This idempotency key was already used for a different request.",
        code="IDEMPOTENCY_KEY_REUSED",
    )
