"""Unit tests for ExecutionPolicy and sub-policies."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.retrieval_engine.policies import (
    CancellationPolicy,
    ExecutionPolicy,
    PartialResultPolicy,
    RetryPolicy,
    TimeoutPolicy,
)


def test_execution_policy_defaults():
    policy = ExecutionPolicy()
    assert policy.retry.max_attempts == 1
    assert policy.timeout.per_retriever_ms is None
    assert policy.cancellation.cancel_on_budget_exceeded is True
    assert policy.partial_result.allow_partial is True


def test_execution_policy_frozen():
    policy = ExecutionPolicy()
    with pytest.raises(ValidationError):
        policy.retry = RetryPolicy(max_attempts=3)  # type: ignore[misc]


def test_timeout_policy_defaults():
    t = TimeoutPolicy()
    assert t.per_retriever_ms is None
    assert t.total_pipeline_ms is None


def test_retry_policy_defaults():
    r = RetryPolicy()
    assert r.max_attempts == 1
    assert r.backoff_ms == 0
    assert r.retryable_on == ()


def test_cancellation_policy_defaults():
    c = CancellationPolicy()
    assert c.cancel_on_budget_exceeded is True
    assert c.cancel_on_timeout is True


def test_partial_result_policy_defaults():
    p = PartialResultPolicy()
    assert p.allow_partial is True
    assert p.min_candidates_required == 0


def test_nested_policy_composition():
    policy = ExecutionPolicy(
        timeout=TimeoutPolicy(per_retriever_ms=100),
        retry=RetryPolicy(max_attempts=3, backoff_ms=10),
        cancellation=CancellationPolicy(cancel_on_budget_exceeded=False),
        partial_result=PartialResultPolicy(allow_partial=False, min_candidates_required=5),
    )
    assert policy.timeout.per_retriever_ms == 100
    assert policy.retry.max_attempts == 3
    assert policy.cancellation.cancel_on_budget_exceeded is False
    assert policy.partial_result.min_candidates_required == 5
