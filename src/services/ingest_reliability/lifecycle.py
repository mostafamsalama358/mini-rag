"""Lifecycle transition guards for ingest jobs (contracts/job-lifecycle.md)."""

from __future__ import annotations

from services.ingest_reliability.models import LifecycleState

TERMINAL_STATES: frozenset[LifecycleState] = frozenset(
    {
        LifecycleState.COMPLETED,
        LifecycleState.COMPLETED_WITH_WARNINGS,
        LifecycleState.FAILED,
        LifecycleState.CANCELLED,
        LifecycleState.TIMED_OUT,
    }
)

# Allowed directed edges (from -> to). Incomplete graph is intentional: unknown
# edges are rejected unless listed.
_ALLOWED: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.ACCEPTED: frozenset(
        {
            LifecycleState.VALIDATING,
            LifecycleState.CANCELLED,
            LifecycleState.TIMED_OUT,
            LifecycleState.FAILED,
        }
    ),
    LifecycleState.VALIDATING: frozenset(
        {
            LifecycleState.PARSING,
            LifecycleState.FAILED,
            LifecycleState.CANCELLED,
            LifecycleState.TIMED_OUT,
        }
    ),
    LifecycleState.PARSING: frozenset(
        {
            LifecycleState.DEGRADED_PARSING,
            LifecycleState.CHUNK_PREPARATION,
            LifecycleState.FAILED,
            LifecycleState.CANCELLED,
            LifecycleState.TIMED_OUT,
        }
    ),
    LifecycleState.DEGRADED_PARSING: frozenset(
        {
            LifecycleState.CHUNK_PREPARATION,
            LifecycleState.FAILED,
            LifecycleState.CANCELLED,
            LifecycleState.TIMED_OUT,
        }
    ),
    LifecycleState.CHUNK_PREPARATION: frozenset(
        {
            LifecycleState.ENRICHMENT,
            LifecycleState.FAILED,
            LifecycleState.CANCELLED,
            LifecycleState.TIMED_OUT,
        }
    ),
    LifecycleState.ENRICHMENT: frozenset(
        {
            LifecycleState.INDEXING,
            LifecycleState.FAILED,
            LifecycleState.CANCELLED,
            LifecycleState.TIMED_OUT,
        }
    ),
    LifecycleState.INDEXING: frozenset(
        {
            LifecycleState.PUBLISHING,
            LifecycleState.FAILED,
            LifecycleState.CANCELLED,
            LifecycleState.TIMED_OUT,
        }
    ),
    LifecycleState.PUBLISHING: frozenset(
        {
            LifecycleState.COMPLETED,
            LifecycleState.COMPLETED_WITH_WARNINGS,
            LifecycleState.FAILED,
            LifecycleState.CANCELLED,
            LifecycleState.TIMED_OUT,
        }
    ),
}


def is_terminal(state: LifecycleState) -> bool:
    return state in TERMINAL_STATES


def can_transition(current: LifecycleState, new_state: LifecycleState) -> bool:
    if current == new_state:
        return True
    if is_terminal(current):
        return False
    allowed = _ALLOWED.get(current, frozenset())
    return new_state in allowed


class IllegalLifecycleTransition(ValueError):
    """Raised when a transition violates the job-lifecycle contract."""


def transition_job(
    *,
    current: LifecycleState,
    new_state: LifecycleState,
    cause: str,
) -> LifecycleState:
    """Validate and return the new lifecycle state.

    ``cause`` is required for audit callers; unused for pure validation.
    """
    _ = cause
    if not can_transition(current, new_state):
        raise IllegalLifecycleTransition(
            f"Illegal lifecycle transition {current.value!r} -> {new_state.value!r}"
        )
    return new_state
