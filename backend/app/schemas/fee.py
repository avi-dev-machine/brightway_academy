from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.fee import FeeType

MAX_AMOUNT_PAISE = 10_000_000_00  # INR 1 crore


class FeePlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    course_id: UUID | None = None
    plan_type: FeeType
    amount_paise: int = Field(
        gt=0,
        le=MAX_AMOUNT_PAISE,
        description=(
            "MONTHLY/ONE_TIME: amount per fee. INSTALLMENT: total split across installments."
        ),
    )
    installment_count: int = Field(default=1, ge=1, le=60)

    @model_validator(mode="after")
    def _check(self) -> "FeePlanCreate":
        if self.plan_type == FeeType.ONE_TIME and self.installment_count != 1:
            raise ValueError("A ONE_TIME plan has exactly one installment.")
        if self.plan_type == FeeType.INSTALLMENT and self.amount_paise < self.installment_count:
            raise ValueError("Amount is too small for that many installments.")
        return self


class FeePlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    active: bool | None = None


class AssignPlanRequest(BaseModel):
    fee_plan_id: UUID
    start_date: date = Field(description="Due date of the first fee; later ones follow monthly.")


class FeeCreate(BaseModel):
    student_id: UUID
    title: str = Field(min_length=1, max_length=200)
    amount_paise: int = Field(gt=0, le=MAX_AMOUNT_PAISE)
    due_date: date
    fee_type: FeeType = FeeType.ONE_TIME


class ConcessionRequest(BaseModel):
    amount_paise: int = Field(gt=0, le=MAX_AMOUNT_PAISE)
    reason: str = Field(min_length=3, max_length=300)


class CancelFeeRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


class FeeSummary(BaseModel):
    student_id: UUID
    total_amount_paise: int
    total_concession_paise: int
    total_paid_paise: int
    total_outstanding_paise: int
    overdue_count: int
    overdue_paise: int
