"""Golden e2e integration suite for Retrieval Engine V2."""

from __future__ import annotations

import pytest

from core.retrieval_engine.budget.enforcer import BudgetEnforcer
from core.retrieval_engine.errors import InsufficientCandidatesError
from core.retrieval_engine.expansion.passthrough import PassthroughExpander
from core.retrieval_engine.fusion.rrf import RRFScoreFuser
from core.retrieval_engine.interfaces import IQueryExpander, IRetriever
from core.retrieval_engine.models import (
    ExpansionContext,
    ExpansionResult,
    RawCandidate,
    RetrievalEngineConfig,
    SourceRef,
)
from core.retrieval_engine.pipeline import RetrievalEnginePipeline
from core.retrieval_engine.policies import (
    CancellationPolicy,
    ExecutionPolicy,
    PartialResultPolicy,
    RetryPolicy,
    TimeoutPolicy,
)
from core.retrieval_engine.registry import RetrieverRegistry
from core.retrieval_engine.reranking.passthrough import PassthroughReranker
from core.retrieval_engine.router import StrategyRouter
from core.retrieval_engine.tracing.tracer import RetrievalTracer
from tests.unit.core.retrieval_engine.conftest import mock_retriever, plan_builder


def _c(chunk_id: str, strategy: str, score: float = 0.9) -> RawCandidate:
    return RawCandidate(
        chunk_id=chunk_id,
        document_id="doc1",
        raw_score=score,
        retriever_id=f"mock_{strategy}",
        strategy=strategy,
        expander_variant_id="v0",
        content_excerpt=chunk_id,
        source_ref=SourceRef(document_id="doc1", chunk_id=chunk_id),
    )


def _pipe(retrievers: dict[str, IRetriever], **kwargs) -> RetrievalEnginePipeline:
    return RetrievalEnginePipeline(
        expander=kwargs.get("expander") or PassthroughExpander(),
        router=StrategyRouter(lambda s: retrievers.get(s)),
        fuser=RRFScoreFuser(),
        reranker=kwargs.get("reranker") or PassthroughReranker(),
        budget_enforcer=BudgetEnforcer(),
        tracer_factory=RetrievalTracer,
        config=kwargs.get("config") or RetrievalEngineConfig(),
    )


def _assert_valid(result, *, max_evidence: int, expected_steps: int | None = None):
    assert result.schema_version == "1.0.0"
    assert result.result_id.startswith("rr_")
    assert len(result.candidates) <= max_evidence
    ids = [c.chunk_id for c in result.candidates]
    assert len(ids) == len(set(ids))
    if expected_steps is not None:
        assert len(result.trace.steps) == expected_steps


@pytest.mark.asyncio
async def test_factual_semantic():
    pipe = _pipe({"semantic": mock_retriever("semantic", [_c("a", "semantic")])})
    plan = plan_builder(["semantic"], max_evidence_units=5)
    result = await pipe.execute(plan)
    _assert_valid(result, max_evidence=5, expected_steps=1)
    again = await pipe.execute(plan)
    assert result.result_id == again.result_id


@pytest.mark.asyncio
async def test_keyword_only():
    pipe = _pipe({"keyword": mock_retriever("keyword", [_c("k", "keyword")])})
    result = await pipe.execute(plan_builder(["keyword"], max_evidence_units=5))
    _assert_valid(result, max_evidence=5, expected_steps=1)


@pytest.mark.asyncio
async def test_hybrid_resolved():
    pipe = _pipe(
        {
            "semantic": mock_retriever("semantic", [_c("a", "semantic")]),
            "keyword": mock_retriever("keyword", [_c("b", "keyword")]),
        },
        config=RetrievalEngineConfig(hybrid_components=["semantic", "keyword"]),
    )
    result = await pipe.execute(plan_builder(["hybrid"], max_evidence_units=5))
    _assert_valid(result, max_evidence=5, expected_steps=2)
    assert all(s.strategy != "hybrid" for s in result.trace.steps)
    assert result.metadata.hybrid_components_used


@pytest.mark.asyncio
async def test_multi_strategy_2():
    pipe = _pipe(
        {
            "semantic": mock_retriever("semantic", [_c("a", "semantic")]),
            "keyword": mock_retriever("keyword", [_c("b", "keyword")]),
        }
    )
    result = await pipe.execute(
        plan_builder(["semantic", "keyword"], max_evidence_units=5)
    )
    _assert_valid(result, max_evidence=5, expected_steps=2)


@pytest.mark.asyncio
async def test_multi_strategy_3():
    pipe = _pipe(
        {
            "semantic": mock_retriever("semantic", [_c("a", "semantic")]),
            "keyword": mock_retriever("keyword", [_c("b", "keyword")]),
            "metadata": mock_retriever("metadata", [_c("c", "metadata")]),
        }
    )
    result = await pipe.execute(
        plan_builder(["semantic", "keyword", "metadata"], max_evidence_units=5)
    )
    _assert_valid(result, max_evidence=5, expected_steps=3)


@pytest.mark.asyncio
async def test_structured_plan():
    pipe = _pipe(
        {"structured": mock_retriever("structured", [_c("s", "structured")])}
    )
    result = await pipe.execute(plan_builder(["structured"], max_evidence_units=5))
    _assert_valid(result, max_evidence=5, expected_steps=1)


@pytest.mark.asyncio
async def test_multi_query_expansion():
    class _Exp(IQueryExpander):
        @property
        def expander_id(self) -> str:
            return "mock"

        @property
        def expansion_type(self) -> str:
            return "mock"

        def expand(self, context: ExpansionContext) -> ExpansionResult:
            return ExpansionResult(variants=("a", "b", "c"), expansion_type="mock")

    pipe = _pipe(
        {"semantic": mock_retriever("semantic", [_c("x", "semantic")])},
        expander=_Exp(),
    )
    result = await pipe.execute(plan_builder(["semantic"], max_evidence_units=5))
    _assert_valid(result, max_evidence=5, expected_steps=3)


@pytest.mark.asyncio
async def test_empty_strategies():
    pipe = _pipe({})
    result = await pipe.execute(
        plan_builder([], clarification_required=True, max_evidence_units=5)
    )
    _assert_valid(result, max_evidence=5, expected_steps=0)


@pytest.mark.asyncio
async def test_budget_cap():
    many = [_c(f"c{i}", "semantic", 1.0 - i * 0.01) for i in range(20)]
    pipe = _pipe({"semantic": mock_retriever("semantic", many)})
    result = await pipe.execute(
        plan_builder(["semantic"], max_candidates=10, max_evidence_units=3)
    )
    assert len(result.candidates) <= 3


@pytest.mark.asyncio
async def test_timeout_policy():
    pipe = _pipe(
        {
            "semantic": mock_retriever("semantic", [_c("ok", "semantic")]),
            "keyword": mock_retriever("keyword", [_c("slow", "keyword")], sleep_ms=80),
        }
    )
    result = await pipe.execute(
        plan_builder(["semantic", "keyword"], max_evidence_units=5),
        policy=ExecutionPolicy(timeout=TimeoutPolicy(per_retriever_ms=5)),
    )
    assert any(s.skip_reason == "timeout" for s in result.trace.steps)


@pytest.mark.asyncio
async def test_retry_policy():
    pipe = _pipe(
        {"semantic": mock_retriever("semantic", [_c("ok", "semantic")], fail_times=2)}
    )
    result = await pipe.execute(
        plan_builder(["semantic"], max_evidence_units=5),
        policy=ExecutionPolicy(retry=RetryPolicy(max_attempts=3)),
    )
    assert result.candidates
    assert result.trace.steps[0].retry_count == 2


@pytest.mark.asyncio
async def test_partial_allowed():
    pipe = _pipe({"semantic": mock_retriever("semantic", [])})
    result = await pipe.execute(
        plan_builder(["semantic"], max_evidence_units=5),
        policy=ExecutionPolicy(
            partial_result=PartialResultPolicy(
                allow_partial=True, min_candidates_required=3
            )
        ),
    )
    assert result.partial is True


@pytest.mark.asyncio
async def test_partial_forbidden():
    pipe = _pipe({"semantic": mock_retriever("semantic", [])})
    with pytest.raises(InsufficientCandidatesError):
        await pipe.execute(
            plan_builder(["semantic"], max_evidence_units=5),
            policy=ExecutionPolicy(
                partial_result=PartialResultPolicy(
                    allow_partial=False, min_candidates_required=3
                )
            ),
        )


@pytest.mark.asyncio
async def test_custom_retriever():
    class Custom(IRetriever):
        @property
        def retriever_id(self) -> str:
            return "custom"

        @property
        def supported_strategy(self) -> str:
            return "custom_v1"

        async def retrieve(self, query, context):
            return [_c("cust", "custom_v1")]

    registry = RetrieverRegistry()
    registry.register_retriever(Custom())
    registry.register_expander(PassthroughExpander())
    registry.register_fuser(RRFScoreFuser())
    registry.register_reranker(PassthroughReranker())
    pipe = RetrievalEnginePipeline(
        expander=registry.get_expander("passthrough"),
        router=StrategyRouter(registry.get_retriever),
        fuser=registry.get_fuser("rrf"),
        reranker=registry.get_reranker("passthrough"),
        budget_enforcer=BudgetEnforcer(),
        tracer_factory=RetrievalTracer,
        config=RetrievalEngineConfig(),
    )
    result = await pipe.execute(plan_builder(["custom_v1"], max_evidence_units=5))
    _assert_valid(result, max_evidence=5, expected_steps=1)
    assert result.candidates[0].chunk_id == "cust"
