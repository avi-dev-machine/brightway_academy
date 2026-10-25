from datetime import date

import pytest

from app.models.fee import FeeStatus, FeeType, build_plan_schedule, compute_fee_status, split_amount
from app.utils.dates import add_months

TODAY = date(2026, 10, 7)


def status(amount=10_000, concession=0, paid=0, due=date(2026, 10, 20), current=None):
    return compute_fee_status(
        amount_paise=amount,
        concession_paise=concession,
        paid_paise=paid,
        due_date=due,
        today=TODAY,
        current=current,
    )


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({}, FeeStatus.PENDING),
        ({"paid": 4_000}, FeeStatus.PARTIALLY_PAID),
        ({"paid": 10_000}, FeeStatus.PAID),
        ({"concession": 2_000, "paid": 8_000}, FeeStatus.PAID),
        ({"concession": 10_000}, FeeStatus.PAID),
        ({"due": date(2026, 10, 1)}, FeeStatus.OVERDUE),
        ({"due": date(2026, 10, 1), "paid": 5_000}, FeeStatus.OVERDUE),
        ({"due": date(2026, 10, 7)}, FeeStatus.PENDING),  # due today is not overdue yet
        ({"paid": 12_000}, FeeStatus.PAID),  # overpayment still counts as paid
        ({"current": FeeStatus.CANCELLED}, FeeStatus.CANCELLED),
    ],
)
def test_compute_fee_status(kwargs, expected):
    assert status(**kwargs) == expected


def test_split_amount_puts_remainder_on_last_installment():
    assert split_amount(100_000, 3) == [33_333, 33_333, 33_334]
    assert sum(split_amount(99_999, 7)) == 99_999


@pytest.mark.parametrize(("total", "parts"), [(100, 0), (2, 3)])
def test_split_amount_rejects_invalid_input(total, parts):
    with pytest.raises(ValueError):
        split_amount(total, parts)


def test_add_months_clamps_to_month_end():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 11, 15), 3) == date(2027, 2, 15)
    assert add_months(date(2028, 1, 31), 1) == date(2028, 2, 29)


def test_monthly_schedule():
    items = build_plan_schedule(
        plan_type=FeeType.MONTHLY,
        plan_name="DCA Monthly",
        amount_paise=150_000,
        installment_count=3,
        start_date=date(2026, 10, 5),
    )
    assert [i.title for i in items] == [
        "DCA Monthly - Oct 2026",
        "DCA Monthly - Nov 2026",
        "DCA Monthly - Dec 2026",
    ]
    assert {i.amount_paise for i in items} == {150_000}
    assert [i.installment_no for i in items] == [1, 2, 3]


def test_installment_schedule_splits_total():
    items = build_plan_schedule(
        plan_type=FeeType.INSTALLMENT,
        plan_name="DCA",
        amount_paise=1_000_000,
        installment_count=3,
        start_date=date(2026, 1, 31),
    )
    assert sum(i.amount_paise for i in items) == 1_000_000
    assert [i.due_date for i in items] == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)]
    assert items[0].title == "DCA - Installment 1/3"


def test_one_time_schedule():
    items = build_plan_schedule(
        plan_type=FeeType.ONE_TIME,
        plan_name="Admission",
        amount_paise=50_000,
        installment_count=1,
        start_date=TODAY,
    )
    assert len(items) == 1 and items[0].title == "Admission" and items[0].due_date == TODAY
