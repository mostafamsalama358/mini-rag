import pytest

from services.ingest_reliability.lifecycle import (
    IllegalLifecycleTransition,
    TERMINAL_STATES,
    can_transition,
    is_terminal,
    transition_job,
)
from services.ingest_reliability.models import LifecycleState


def test_accepted_to_validating():
    assert can_transition(LifecycleState.ACCEPTED, LifecycleState.VALIDATING)
    assert (
        transition_job(
            current=LifecycleState.ACCEPTED,
            new_state=LifecycleState.VALIDATING,
            cause="start",
        )
        == LifecycleState.VALIDATING
    )


def test_terminal_irreversible():
    for state in TERMINAL_STATES:
        assert is_terminal(state)
        assert not can_transition(state, LifecycleState.PARSING)


def test_illegal_skip_to_completed():
    with pytest.raises(IllegalLifecycleTransition):
        transition_job(
            current=LifecycleState.PARSING,
            new_state=LifecycleState.COMPLETED,
            cause="bad",
        )


def test_publishing_to_completed_with_warnings():
    assert can_transition(
        LifecycleState.PUBLISHING, LifecycleState.COMPLETED_WITH_WARNINGS
    )
