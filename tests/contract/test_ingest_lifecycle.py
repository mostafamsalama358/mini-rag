"""Contract tests for ingest job lifecycle (spec 017).

Placeholder module created in Phase 1; scenarios filled as lifecycle lands.
"""

from services.ingest_reliability.lifecycle import TERMINAL_STATES, can_transition
from services.ingest_reliability.models import LifecycleState


def test_terminal_states_are_irreversible():
    for state in TERMINAL_STATES:
        assert can_transition(state, LifecycleState.PARSING) is False


def test_publishing_can_complete():
    assert can_transition(LifecycleState.PUBLISHING, LifecycleState.COMPLETED) is True
    assert can_transition(
        LifecycleState.PUBLISHING, LifecycleState.COMPLETED_WITH_WARNINGS
    ) is True
