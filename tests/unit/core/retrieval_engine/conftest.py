"""Shared fixtures for Retrieval Engine unit tests."""

from __future__ import annotations

from typing import Any, Callable

import pytest

from core.retrieval_engine.interfaces import IReranker, IRetriever, IScoreFuser
from core.retrieval_engine.models import (
    SCHEMA_VERSION,
    RawCandidate,
    SourceRef,
)
from core.retrieval_engine.policies import (
    CancellationPolicy,
    ExecutionPolicy,
    PartialResultPolicy,
    RetryPolicy,
    TimeoutPolicy,
)
from core.retrieval_planner.models import (
    OutputShape,
    QueryIntent,
    RetrievalConstraints,
    RetrievalLimits,
    RetrievalPlan,
    RetrievalPlanMetadata,
)


def mock_retriever(
    strategy: str,
    candidates: list[RawCandidate] | None = None,
    *,
    retriever_id: str | None = None,
    fail_times: int = 0,
    sleep_ms: float = 0,
) -> IRetriever:
    """Factory for a configurable mock IRetriever."""
    calls = {"n": 0, "failures_left": fail_times}

    class _MockRetriever(IRetriever):
        @property
        def retriever_id(self) -> str:
            return retriever_id or f"mock_{strategy}"

        @property
        def supported_strategy(self) -> str:
            return strategy

        async def retrieve(self, query, context):
            import asyncio

            calls["n"] += 1
            if sleep_ms > 0:
                await asyncio.sleep(sleep_ms / 1000.0)
            if calls["failures_left"] > 0:
                calls["failures_left"] -= 1
                raise RuntimeError(f"mock failure for {strategy}")
            if candidates is not None:
                return list(candidates)
            return [
                RawCandidate(
                    chunk_id=f"{strategy}_c1",
                    document_id="doc1",
                    raw_score=0.9,
                    retriever_id=self.retriever_id,
                    strategy=strategy,
                    expander_variant_id=query.expander_variant_id,
                    content_excerpt=f"excerpt for {query.query_text}",
                    source_ref=SourceRef(
                        document_id="doc1",
                        chunk_id=f"{strategy}_c1",
                        page_number=1,
                    ),
                )
            ]

    impl = _MockRetriever()
    impl.calls = calls  # type: ignore[attr-defined]
    return impl


def mock_reranker(*, reverse: bool = False, sleep_ms: float = 0) -> IReranker:
    class _MockReranker(IReranker):
        @property
        def reranker_id(self) -> str:
            return "mock_reranker" if reverse or sleep_ms else "passthrough"

        async def rerank(self, query_text: str, candidates: list[RawCandidate]):
            import asyncio

            if sleep_ms > 0:
                await asyncio.sleep(sleep_ms / 1000.0)
            ordered = list(reversed(candidates)) if reverse else list(candidates)
            return ordered

    return _MockReranker()


def mock_fuser() -> IScoreFuser:
    class _MockFuser(IScoreFuser):
        @property
        def fuser_id(self) -> str:
            return "rrf"

        def fuse(self, ranked_lists: list[list[RawCandidate]]) -> list[RawCandidate]:
            seen: dict[str, RawCandidate] = {}
            for lst in ranked_lists:
                for c in lst:
                    if c.chunk_id not in seen:
                        seen[c.chunk_id] = c
            return list(seen.values())

    return _MockFuser()


def policy_default() -> ExecutionPolicy:
    return ExecutionPolicy()


def policy_strict_timeout(ms: int) -> ExecutionPolicy:
    return ExecutionPolicy(timeout=TimeoutPolicy(per_retriever_ms=ms))


def policy_retry(attempts: int) -> ExecutionPolicy:
    return ExecutionPolicy(retry=RetryPolicy(max_attempts=attempts, backoff_ms=0))


def policy_no_partial(*, min_candidates: int = 5) -> ExecutionPolicy:
    return ExecutionPolicy(
        partial_result=PartialResultPolicy(
            allow_partial=False,
            min_candidates_required=min_candidates,
        )
    )


def plan_builder(
    strategies: list[str] | tuple[str, ...],
    *,
    max_candidates: int = 50,
    max_evidence_units: int = 10,
    citation_required: bool = True,
    canonical_query: str = "test query",
    plan_id: str = "rp_" + "a" * 16,
    clarification_required: bool = False,
) -> RetrievalPlan:
    empty = clarification_required or len(strategies) == 0
    return RetrievalPlan(
        canonical_query=canonical_query,
        intent=QueryIntent(category="factual", confidence=0.9),
        entities=(),
        filters=(),
        retrieval_strategies=tuple(strategies) if not empty else (),
        retrieval_limits=RetrievalLimits(
            max_evidence_units=max(1, max_evidence_units) if max_evidence_units > 0 else 1,
            max_candidates=max(max_candidates, max_evidence_units, 1),
            scope="narrow",
        ),
        retrieval_constraints=RetrievalConstraints(citation_required=citation_required),
        execution_hints=None,
        output_shape=OutputShape(
            shape_type="single_fact", max_items=None, structured=False
        ),
        clarification_required=clarification_required,
        clarification_question="Please clarify?" if clarification_required else None,
        planner_confidence=0.9,
        diagnostics=None,
        metadata=RetrievalPlanMetadata(
            plan_id=plan_id,
            planner_version="1.0.0",
            schema_version=SCHEMA_VERSION,
            config_hash="deadbeef",
            created_at="2026-07-14T00:00:00Z",
        ),
    )


@pytest.fixture
def plan_semantic() -> RetrievalPlan:
    return plan_builder(["semantic"], max_evidence_units=5, max_candidates=20)


@pytest.fixture
def plan_keyword() -> RetrievalPlan:
    return plan_builder(["keyword"], max_evidence_units=5, max_candidates=20)


@pytest.fixture
def plan_multi_strategy() -> RetrievalPlan:
    return plan_builder(
        ["semantic", "keyword"], max_evidence_units=5, max_candidates=20
    )


@pytest.fixture
def plan_hybrid() -> RetrievalPlan:
    return plan_builder(["hybrid"], max_evidence_units=5, max_candidates=20)


@pytest.fixture
def plan_empty_strategies() -> RetrievalPlan:
    return plan_builder(
        [],
        clarification_required=True,
        max_evidence_units=5,
        max_candidates=20,
    )


@pytest.fixture
def plan_with_budget() -> RetrievalPlan:
    return plan_builder(["semantic"], max_candidates=3, max_evidence_units=2)
