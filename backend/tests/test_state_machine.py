import pytest

pytestmark = pytest.mark.l1

from app.models import ReqStatus as S
from app.state_machine import can_transition


def test_review_branches():
    assert can_transition(S.pending_review, S.feasible)
    assert can_transition(S.pending_review, S.info_needed)
    assert can_transition(S.pending_review, S.plan_needed)
    assert can_transition(S.pending_review, S.infeasible)


def test_adjust_returns_to_review():
    assert can_transition(S.info_needed, S.pending_review)
    assert can_transition(S.plan_needed, S.pending_review)


def test_infeasible_reopen():
    assert can_transition(S.infeasible, S.pending_review)


def test_illegal_transitions_rejected():
    assert not can_transition(S.draft, S.delivered)
    assert not can_transition(S.delivered, S.in_dev)
    assert not can_transition(S.draft, S.infeasible)
