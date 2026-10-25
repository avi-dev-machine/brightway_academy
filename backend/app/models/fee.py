"""Fee domain: records plus the pure rules for balances, statuses and schedules."""

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, computed_field

from app.utils.dates import add_months


class FeeType(StrEnum):
    MONTHLY = "MONTHLY"
    INSTALLMENT = "INSTALLMENT"
    ONE_TIME = "ONE_TIME"


class FeeStatus(StrEnum):
    PENDING = "PENDING"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


UNPAID_STATUSES = (FeeStatus.PENDING, FeeStatus.PARTIALLY_PAID, FeeStatus.OVERDUE)


class FeePlan(BaseModel):
    id: UUID
    name: str
    course_id: UUID | None
    plan_type: FeeType
    amount_paise: int
    installment_count: int
    active: bool
    created_at: datetime
    updated_at: datetime


class Fee(BaseModel):
    id: UUID
    student_id: UUID
    fee_plan_id: UUID | None
    fee_type: FeeType
    title: str
    installment_no: int | None
    amount_paise: int
    concession_paise: int
    paid_paise: int
    due_date: date
    status: FeeStatus
    concession_reason: str | None
    cancellation_reason: str | None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def balance_paise(self) -> int:
        return max(outstanding(self.amount_paise, self.concession_paise, self.paid_paise), 0)


def outstanding(amount_paise: int, concession_paise: int, paid_paise: int) -> int:
    """Amount still owed. Negative when the fee was overpaid."""
    return amount_paise - concession_paise - paid_paise


def compute_fee_status(
    *,
    amount_paise: int,
    concession_paise: int,
    paid_paise: int,
    due_date: date,
    today: date,
    current: FeeStatus | None = None,
) -> FeeStatus:
    """Derive a fee's status from its money and due date. CANCELLED is sticky.

    An unpaid fee past its due date is OVERDUE even when partially paid, because
    overdue is the more urgent state for reminders and reports.
    """
    if current == FeeStatus.CANCELLED:
        return FeeStatus.CANCELLED
    if outstanding(amount_paise, concession_paise, paid_paise) <= 0:
        return FeeStatus.PAID
    if due_date < today:
        return FeeStatus.OVERDUE
    if paid_paise > 0:
        return FeeStatus.PARTIALLY_PAID
    return FeeStatus.PENDING


def split_amount(total_paise: int, parts: int) -> list[int]:
    """Split a total into `parts` installments; the rounding remainder goes on the last one."""
    if parts < 1:
        raise ValueError("parts must be at least 1")
    if total_paise < parts:
        raise ValueError("total is too small to split into that many installments")
    base = total_paise // parts
    amounts = [base] * parts
    amounts[-1] += total_paise - base * parts
    return amounts


@dataclass(frozen=True)
class FeeItemSpec:
    title: str
    installment_no: int
    amount_paise: int
    due_date: date


def build_plan_schedule(
    *,
    plan_type: FeeType,
    plan_name: str,
    amount_paise: int,
    installment_count: int,
    start_date: date,
) -> list[FeeItemSpec]:
    """Expand a fee plan into dated fee items, one per month starting at `start_date`."""
    if plan_type == FeeType.ONE_TIME:
        return [FeeItemSpec(plan_name, 1, amount_paise, start_date)]
    if plan_type == FeeType.INSTALLMENT:
        amounts = split_amount(amount_paise, installment_count)
        return [
            FeeItemSpec(
                f"{plan_name} - Installment {i}/{installment_count}",
                i,
                amount,
                add_months(start_date, i - 1),
            )
            for i, amount in enumerate(amounts, start=1)
        ]
    items = []
    for i in range(1, installment_count + 1):
        due = add_months(start_date, i - 1)
        items.append(FeeItemSpec(f"{plan_name} - {due:%b %Y}", i, amount_paise, due))
    return items
