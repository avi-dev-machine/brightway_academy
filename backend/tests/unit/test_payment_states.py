import pytest

from app.exceptions import InvalidStateError
from app.models.payment import PaymentStatus as S
from app.models.payment import can_transition, ensure_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.CREATED, S.PENDING),
        (S.CREATED, S.SUCCESS),
        (S.CREATED, S.FAILED),
        (S.PENDING, S.SUCCESS),
        (S.PENDING, S.FAILED),
        (S.FAILED, S.SUCCESS),  # a retried attempt on the same order can still succeed
        (S.SUCCESS, S.REFUNDED),
    ],
)
def test_allowed_transitions(current, target):
    assert can_transition(current, target)
    ensure_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.SUCCESS, S.FAILED),
        (S.SUCCESS, S.PENDING),
        (S.SUCCESS, S.SUCCESS),
        (S.REFUNDED, S.SUCCESS),
        (S.REFUNDED, S.FAILED),
        (S.PENDING, S.CREATED),
        (S.CREATED, S.REFUNDED),
    ],
)
def test_forbidden_transitions(current, target):
    assert not can_transition(current, target)
    with pytest.raises(InvalidStateError):
        ensure_transition(current, target)


def test_every_status_has_transition_rules():
    from app.models.payment import ALLOWED_TRANSITIONS

    assert set(ALLOWED_TRANSITIONS) == set(S)
