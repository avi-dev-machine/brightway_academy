"""Fee plans, student fees, balances, concessions and cancellations."""

from datetime import date
from uuid import UUID

from app.core.permissions import CurrentUser
from app.db.client import Database
from app.db.transactions import translate_constraint_errors
from app.exceptions import (
    ConflictError,
    ForbiddenError,
    InvalidStateError,
    NotFoundError,
    StudentNotFoundError,
    ValidationFailedError,
)
from app.models.fee import (
    Fee,
    FeePlan,
    FeeStatus,
    build_plan_schedule,
    compute_fee_status,
    outstanding,
)
from app.models.student import StudentStatus
from app.repositories.base import Row
from app.repositories.course_repository import CourseRepository
from app.repositories.fee_repository import FeePlanRepository, FeeRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.fee import (
    AssignPlanRequest,
    CancelFeeRequest,
    ConcessionRequest,
    FeeCreate,
    FeePlanCreate,
    FeePlanUpdate,
    FeeSummary,
)
from app.services.audit_service import record_audit
from app.utils.dates import local_today
from app.utils.pagination import Page, PageParams

_PLAN_CONSTRAINTS = {
    "fee_plans_name_lower_key": lambda: ConflictError(
        "A fee plan with this name already exists.", code="DUPLICATE_FEE_PLAN"
    ),
}
_FEE_CONSTRAINTS = {
    "fees_plan_installment_key": lambda: ConflictError(
        "This fee plan is already assigned to the student.", code="FEE_PLAN_ALREADY_ASSIGNED"
    ),
}


def fee_not_found() -> NotFoundError:
    return NotFoundError("Fee was not found.", code="FEE_NOT_FOUND")


def ensure_fee_access(user: CurrentUser, fee: Row) -> None:
    if user.is_admin:
        return
    if user.is_student and fee["student_id"] == user.student_id:
        return
    raise ForbiddenError("You do not have access to this fee.")


class FeeService:
    def __init__(self, db: Database, timezone: str) -> None:
        self.db = db
        self.timezone = timezone

    def _today(self) -> date:
        return local_today(self.timezone)

    # ------------------------------------------------------------------ plans
    def list_plans(self, *, active: bool | None, course_id: UUID | None) -> list[FeePlan]:
        with self.db.transaction() as conn:
            rows = FeePlanRepository(conn).search(active=active, course_id=course_id)
        return [FeePlan.model_validate(r) for r in rows]

    def create_plan(self, actor: CurrentUser, payload: FeePlanCreate) -> FeePlan:
        with self.db.transaction() as conn:
            if payload.course_id and CourseRepository(conn).get_by_id(payload.course_id) is None:
                raise NotFoundError("Course was not found.", code="COURSE_NOT_FOUND")
            with translate_constraint_errors(_PLAN_CONSTRAINTS):
                row = FeePlanRepository(conn).insert(payload.model_dump())
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="fee_plan.created",
                entity_type="fee_plan",
                entity_id=row["id"],
                after=row,
            )
        return FeePlan.model_validate(row)

    def update_plan(self, actor: CurrentUser, plan_id: UUID, payload: FeePlanUpdate) -> FeePlan:
        with self.db.transaction() as conn:
            repo = FeePlanRepository(conn)
            current = repo.get_by_id(plan_id, for_update=True)
            if current is None:
                raise NotFoundError("Fee plan was not found.", code="FEE_PLAN_NOT_FOUND")
            with translate_constraint_errors(_PLAN_CONSTRAINTS):
                row = repo.update_fields(plan_id, payload.model_dump(exclude_unset=True))
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="fee_plan.updated",
                entity_type="fee_plan",
                entity_id=plan_id,
                before=current,
                after=row,
            )
        return FeePlan.model_validate(row)

    # ------------------------------------------------------------------ fees
    def assign_plan(
        self, actor: CurrentUser, student_id: UUID, payload: AssignPlanRequest
    ) -> list[Fee]:
        today = self._today()
        with self.db.transaction() as conn:
            student = StudentRepository(conn).lock(student_id)
            if student is None:
                raise StudentNotFoundError()
            if student["status"] != StudentStatus.ACTIVE:
                raise InvalidStateError(
                    "Fees cannot be assigned to an inactive student.", code="STUDENT_INACTIVE"
                )
            plan = FeePlanRepository(conn).get_by_id(payload.fee_plan_id)
            if plan is None:
                raise NotFoundError("Fee plan was not found.", code="FEE_PLAN_NOT_FOUND")
            if not plan["active"]:
                raise ValidationFailedError("This fee plan is inactive.", code="FEE_PLAN_INACTIVE")
            items = build_plan_schedule(
                plan_type=plan["plan_type"],
                plan_name=plan["name"],
                amount_paise=plan["amount_paise"],
                installment_count=plan["installment_count"],
                start_date=payload.start_date,
            )
            fees = FeeRepository(conn)
            rows = []
            with translate_constraint_errors(_FEE_CONSTRAINTS):
                for item in items:
                    rows.append(
                        fees.insert(
                            {
                                "student_id": student_id,
                                "fee_plan_id": plan["id"],
                                "fee_type": plan["plan_type"],
                                "title": item.title,
                                "installment_no": item.installment_no,
                                "amount_paise": item.amount_paise,
                                "due_date": item.due_date,
                                "status": compute_fee_status(
                                    amount_paise=item.amount_paise,
                                    concession_paise=0,
                                    paid_paise=0,
                                    due_date=item.due_date,
                                    today=today,
                                ),
                                "created_by": actor.user_id,
                            }
                        )
                    )
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="fee_plan.assigned",
                entity_type="student",
                entity_id=student_id,
                after={"fee_plan_id": str(plan["id"]), "fees_created": len(rows)},
            )
        return [Fee.model_validate(r) for r in rows]

    def create_fee(self, actor: CurrentUser, payload: FeeCreate) -> Fee:
        with self.db.transaction() as conn:
            student = StudentRepository(conn).get_by_id(payload.student_id)
            if student is None:
                raise StudentNotFoundError()
            row = FeeRepository(conn).insert(
                {
                    "student_id": payload.student_id,
                    "fee_type": payload.fee_type,
                    "title": payload.title,
                    "amount_paise": payload.amount_paise,
                    "due_date": payload.due_date,
                    "status": compute_fee_status(
                        amount_paise=payload.amount_paise,
                        concession_paise=0,
                        paid_paise=0,
                        due_date=payload.due_date,
                        today=self._today(),
                    ),
                    "created_by": actor.user_id,
                }
            )
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="fee.created",
                entity_type="fee",
                entity_id=row["id"],
                after=row,
            )
        return Fee.model_validate(row)

    def list_fees(
        self,
        user: CurrentUser,
        *,
        student_id: UUID | None,
        status: FeeStatus | None,
        params: PageParams,
    ) -> Page[Fee]:
        if user.is_teacher:
            raise ForbiddenError()
        if user.is_student:
            if student_id is not None and student_id != user.student_id:
                raise ForbiddenError("You can only view your own fees.")
            student_id = user.student_id
        with self.db.transaction() as conn:
            rows, total = FeeRepository(conn).search(
                student_id=student_id,
                status=status.value if status else None,
                limit=params.limit,
                offset=params.offset,
            )
        return Page([Fee.model_validate(r) for r in rows], total, params)

    def get_fee(self, user: CurrentUser, fee_id: UUID) -> Fee:
        with self.db.transaction() as conn:
            row = FeeRepository(conn).get_by_id(fee_id)
        if row is None:
            raise fee_not_found()
        ensure_fee_access(user, row)
        return Fee.model_validate(row)

    def summary(self, user: CurrentUser, student_id: UUID) -> FeeSummary:
        if not (user.is_admin or (user.is_student and user.student_id == student_id)):
            raise ForbiddenError("You do not have access to this student's fees.")
        with self.db.transaction() as conn:
            if StudentRepository(conn).get_by_id(student_id) is None:
                raise StudentNotFoundError()
            row = FeeRepository(conn).summary_for_student(student_id)
        return FeeSummary(student_id=student_id, **{k: int(v) for k, v in row.items()})

    def apply_concession(self, actor: CurrentUser, fee_id: UUID, payload: ConcessionRequest) -> Fee:
        with self.db.transaction() as conn:
            fees = FeeRepository(conn)
            fee = fees.get_by_id(fee_id, for_update=True)
            if fee is None:
                raise fee_not_found()
            if fee["status"] == FeeStatus.CANCELLED:
                raise InvalidStateError("This fee has been cancelled.", code="FEE_CANCELLED")
            balance = outstanding(fee["amount_paise"], fee["concession_paise"], fee["paid_paise"])
            if payload.amount_paise > balance:
                raise ValidationFailedError(
                    "A concession cannot exceed the outstanding balance.",
                    code="CONCESSION_EXCEEDS_BALANCE",
                    details={"balance_paise": max(balance, 0)},
                )
            concession = fee["concession_paise"] + payload.amount_paise
            reason = payload.reason.strip()
            if fee["concession_reason"]:
                reason = f"{fee['concession_reason']}; {reason}"
            row = fees.update_fields(
                fee_id,
                {
                    "concession_paise": concession,
                    "concession_reason": reason,
                    "status": compute_fee_status(
                        amount_paise=fee["amount_paise"],
                        concession_paise=concession,
                        paid_paise=fee["paid_paise"],
                        due_date=fee["due_date"],
                        today=self._today(),
                        current=FeeStatus(fee["status"]),
                    ),
                },
            )
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="fee.concession_applied",
                entity_type="fee",
                entity_id=fee_id,
                before=fee,
                after=row,
            )
        return Fee.model_validate(row)

    def cancel_fee(self, actor: CurrentUser, fee_id: UUID, payload: CancelFeeRequest) -> Fee:
        with self.db.transaction() as conn:
            fees = FeeRepository(conn)
            fee = fees.get_by_id(fee_id, for_update=True)
            if fee is None:
                raise fee_not_found()
            if fee["status"] == FeeStatus.CANCELLED:
                return Fee.model_validate(fee)
            if fee["paid_paise"] > 0:
                raise InvalidStateError(
                    "A fee with payments cannot be cancelled. Use a concession or a refund.",
                    code="FEE_HAS_PAYMENTS",
                )
            row = fees.update_fields(
                fee_id,
                {"status": FeeStatus.CANCELLED, "cancellation_reason": payload.reason.strip()},
            )
            record_audit(
                conn,
                actor_id=actor.user_id,
                action="fee.cancelled",
                entity_type="fee",
                entity_id=fee_id,
                before=fee,
                after=row,
            )
        return Fee.model_validate(row)

    def mark_overdue(self, today: date | None = None) -> int:
        with self.db.transaction() as conn:
            return FeeRepository(conn).mark_overdue(today or self._today())
