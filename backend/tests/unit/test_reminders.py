from datetime import date

import pytest

from app.workers.fee_reminders import determine_reminder_stage, stage_name

DUE = date(2026, 10, 10)
OFFSETS = [-3, 0, 3, 7]


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 10, 1), None),
        (date(2026, 10, 7), ("DUE_IN_3_DAYS", date(2026, 10, 7))),
        (date(2026, 10, 9), ("DUE_IN_3_DAYS", date(2026, 10, 7))),
        (date(2026, 10, 10), ("DUE_TODAY", DUE)),
        (date(2026, 10, 14), ("OVERDUE_3_DAYS", date(2026, 10, 13))),
        # After a scheduler outage only the latest stage is due, not a burst of old ones.
        (date(2026, 11, 30), ("OVERDUE_7_DAYS", date(2026, 10, 17))),
    ],
)
def test_determine_reminder_stage(today, expected):
    assert determine_reminder_stage(DUE, today, OFFSETS) == expected


def test_unsorted_offsets_are_handled():
    assert determine_reminder_stage(DUE, date(2026, 10, 10), [7, 0, -3]) == ("DUE_TODAY", DUE)


def test_stage_names():
    assert stage_name(-2) == "DUE_IN_2_DAYS"
    assert stage_name(0) == "DUE_TODAY"
    assert stage_name(14) == "OVERDUE_14_DAYS"
