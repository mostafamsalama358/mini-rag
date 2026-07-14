"""Full pipeline tests for Retrieval Engine (US1–US6)."""

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
from tests.unit.core.retrieval_engine.conftest import (
    mock_reranker,
    mock_retriever,
    plan_builder,
)


def _cand(chunk_id: str, strategy: str, score: float = 0.9) -> RawCandidate:
    return RawCandidate(
        chunk_id=chunk_id,
        document_id="doc1",
        raw_score=score,
        retriever_id=f"mock_{strategy}",
        strategy=strategy,
        expander_variant_id="v0",
        content_excerpt=f"text {chunk_id}",
        source_ref=SourceRef(document_id="doc1", chunk_id=chunk_id, page_number=1),
    )


def _pipeline(
    *,
    retrievers: dict[str, IRetriever],
    expander=None,
    reranker=None,
    config: RetrievalEngineConfig | None = None,
) -> RetrievalEnginePipeline:
    return RetrievalEnginePipeline(
        expander=expander or PassthroughExpander(),
        router=StrategyRouter(lambda s: retrievers.get(s)),
        fuser=RRFScoreFuser(),
        reranker=reranker or PassthroughReranker(),
        budget_enforcer=BudgetEnforcer(),
        tracer_factory=RetrievalTracer,
        config=config or RetrievalEngineConfig(),
    )


# --- US1 ---


@pytest.mark.asyncio
async def test_semantic_single_strategy(plan_semantic):
    ret = mock_retriever(
        "semantic",
        [_cand("c1", "semantic"), _cand("c2", "semantic", 0.8), _cand("c3", "semantic", 0.7)],
    )
    pipe = _pipeline(retrievers={"semantic": ret})
    result = await pipe.execute(plan_semantic)
    assert len(result.candidates) <= plan_semantic.retrieval_limits.max_evidence_units
    for c in result.candidates:
        assert c.score > 0
        assert c.score_source in ("raw", "fusion")
        assert c.source_ref is not None
    assert len(result.trace.steps) == 1
    assert result.metadata.reranker_used is False
    assert result.partial is False
    assert result.metadata.hybrid_components_used == ()
    again = await pipe.execute(plan_semantic)
    assert result.result_id == again.result_id
    assert result.result_id.startswith("rr_")
    assert len(result.result_id) == 19


# --- US2 ---


@pytest.mark.asyncio
async def test_multi_strategy_no_duplicates(plan_multi_strategy):
    r1 = mock_retriever(
        "semantic",
        [_cand("shared", "semantic"), _cand("s_only", "semantic", 0.7)],
    )
    r2 = mock_retriever(
        "keyword",
        [_cand("shared", "keyword", 0.85), _cand("k_only", "keyword", 0.6)],
    )
    pipe = _pipeline(retrievers={"semantic": r1, "keyword": r2})
    result = await pipe.execute(plan_multi_strategy)
    ids = [c.chunk_id for c in result.candidates]
    assert len(ids) == len(set(ids))
    assert len(result.trace.steps) == 2
    assert result.metadata.fusion_algorithm == "rrf"


@pytest.mark.asyncio
async def test_hybrid_meta_strategy_resolution(plan_hybrid):
    r1 = mock_retriever("semantic", [_cand("a", "semantic")])
    r2 = mock_retriever("keyword", [_cand("b", "keyword")])
    pipe = _pipeline(
        retrievers={"semantic": r1, "keyword": r2},
        config=RetrievalEngineConfig(hybrid_components=["semantic", "keyword"]),
    )
    result = await pipe.execute(plan_hybrid)
    assert len(result.trace.steps) == 2
    assert result.metadata.hybrid_components_used == ("semantic", "keyword")
    assert all(s.strategy != "hybrid" for s in result.trace.steps)


# --- US3 ---


@pytest.mark.asyncio
async def test_rerank_reverses_order(plan_semantic):
    ret = mock_retriever(
        "semantic",
        [_cand("c1", "semantic", 0.9), _cand("c2", "semantic", 0.8)],
    )
    pipe = _pipeline(
        retrievers={"semantic": ret},
        reranker=mock_reranker(reverse=True),
    )
    result = await pipe.execute(plan_semantic)
    assert [c.chunk_id for c in result.candidates] == ["c2", "c1"]
    assert result.metadata.reranker_used is True
    assert all(c.score_source == "reranker" for c in result.candidates)


@pytest.mark.asyncio
async def test_passthrough_reranker_preserves_order(plan_semantic):
    ret = mock_retriever(
        "semantic",
        [_cand("c1", "semantic", 0.9), _cand("c2", "semantic", 0.8)],
    )
    pipe = _pipeline(retrievers={"semantic": ret}, reranker=PassthroughReranker())
    result = await pipe.execute(plan_semantic)
    assert [c.chunk_id for c in result.candidates] == ["c1", "c2"]
    assert result.metadata.reranker_used is False


@pytest.mark.asyncio
async def test_rerank_timeout_uses_fusion_order(plan_semantic):
    ret = mock_retriever(
        "semantic",
        [_cand("c1", "semantic", 0.9), _cand("c2", "semantic", 0.8)],
    )
    pipe = _pipeline(
        retrievers={"semantic": ret},
        reranker=mock_reranker(reverse=True, sleep_ms=100),
    )
    result = await pipe.execute(
        plan_semantic,
        policy=ExecutionPolicy(timeout=TimeoutPolicy(per_retriever_ms=1)),
    )
    assert result.partial is True
    assert any("reranker_timeout" in v for v in result.trace.constraint_violations)
    assert [c.chunk_id for c in result.candidates] == ["c1", "c2"]


# --- US4 ---


@pytest.mark.asyncio
async def test_expansion_three_variants():
    class _Three(IQueryExpander):
        @property
        def expander_id(self) -> str:
            return "mock"

        @property
        def expansion_type(self) -> str:
            return "mock"

        def expand(self, context: ExpansionContext) -> ExpansionResult:
            return ExpansionResult(
                variants=("q0", "q1", "q2"), expansion_type="mock"
            )

    ret = mock_retriever("semantic", [_cand("c1", "semantic")])
    pipe = _pipeline(retrievers={"semantic": ret}, expander=_Three())
    result = await pipe.execute(plan_builder(["semantic"]))
    assert len(result.trace.steps) == 3
    ids = [c.chunk_id for c in result.candidates]
    assert len(ids) == len(set(ids))
    assert result.metadata.expander_used is True
    assert result.metadata.expander_type == "mock"


@pytest.mark.asyncio
async def test_passthrough_expander_metadata(plan_semantic):
    ret = mock_retriever("semantic", [_cand("c1", "semantic")])
    pipe = _pipeline(retrievers={"semantic": ret})
    result = await pipe.execute(plan_semantic)
    assert result.metadata.expander_used is False
    assert len(result.trace.steps) == 1


@pytest.mark.asyncio
async def test_llm_based_expander_pluggable():
    class LLMBasedExpander(IQueryExpander):
        @property
        def expander_id(self) -> str:
            return "llm"

        @property
        def expansion_type(self) -> str:
            return "llm"

        def expand(self, context: ExpansionContext) -> ExpansionResult:
            return ExpansionResult(
                variants=(context.query_text, context.query_text + " synonym"),
                expansion_type="llm",
            )

    registry = RetrieverRegistry()
    registry.register_expander(LLMBasedExpander())
    registry.register_fuser(RRFScoreFuser())
    registry.register_reranker(PassthroughReranker())
    ret = mock_retriever("semantic", [_cand("c1", "semantic")])
    registry.register_retriever(ret)
    pipe = RetrievalEnginePipeline(
        expander=registry.get_expander("llm"),
        router=StrategyRouter(registry.get_retriever),
        fuser=registry.get_fuser("rrf"),
        reranker=registry.get_reranker("passthrough"),
        budget_enforcer=BudgetEnforcer(),
        tracer_factory=RetrievalTracer,
        config=RetrievalEngineConfig(),
    )
    result = await pipe.execute(plan_builder(["semantic"]))
    assert result.metadata.expander_type == "llm"
    assert len(result.trace.steps) == 2


# --- US5 ---


@pytest.mark.asyncio
async def test_timeout_policy_skips_slow_retriever():
    fast = mock_retriever("semantic", [_cand("fast", "semantic")])
    slow = mock_retriever("keyword", [_cand("slow", "keyword")], sleep_ms=100)
    pipe = _pipeline(retrievers={"semantic": fast, "keyword": slow})
    result = await pipe.execute(
        plan_builder(["semantic", "keyword"]),
        policy=ExecutionPolicy(timeout=TimeoutPolicy(per_retriever_ms=5)),
    )
    timeout_steps = [s for s in result.trace.steps if s.skip_reason == "timeout"]
    assert timeout_steps
    assert timeout_steps[0].skipped is True
    assert any(c.chunk_id == "fast" for c in result.candidates)


@pytest.mark.asyncio
async def test_retry_policy_recovers():
    ret = mock_retriever("semantic", [_cand("ok", "semantic")], fail_times=2)
    pipe = _pipeline(retrievers={"semantic": ret})
    result = await pipe.execute(
        plan_builder(["semantic"]),
        policy=ExecutionPolicy(retry=RetryPolicy(max_attempts=3, backoff_ms=0)),
    )
    assert any(c.chunk_id == "ok" for c in result.candidates)
    assert result.trace.steps[0].retry_count == 2


@pytest.mark.asyncio
async def test_cancellation_on_budget_exceeded():
    r1 = mock_retriever(
        "semantic",
        [_cand("a", "semantic"), _cand("b", "semantic"), _cand("c", "semantic")],
    )
    r2 = mock_retriever("keyword", [_cand("d", "keyword")])
    pipe = _pipeline(retrievers={"semantic": r1, "keyword": r2})
    result = await pipe.execute(
        plan_builder(["semantic", "keyword"], max_candidates=2, max_evidence_units=2),
        policy=ExecutionPolicy(
            cancellation=CancellationPolicy(cancel_on_budget_exceeded=True)
        ),
    )
    skipped = [s for s in result.trace.steps if s.skip_reason == "budget_exhausted"]
    assert skipped
    assert skipped[0].skipped is True
    assert getattr(r2, "calls")["n"] == 0


@pytest.mark.asyncio
async def test_partial_forbidden_raises():
    empty = mock_retriever("semantic", [])
    pipe = _pipeline(retrievers={"semantic": empty})
    with pytest.raises(InsufficientCandidatesError):
        await pipe.execute(
            plan_builder(["semantic"]),
            policy=ExecutionPolicy(
                partial_result=PartialResultPolicy(
                    allow_partial=False, min_candidates_required=5
                )
            ),
        )


# --- US6 ---


@pytest.mark.asyncio
async def test_custom_retriever_via_registry():
    class MockCustomRetriever(IRetriever):
        @property
        def retriever_id(self) -> str:
            return "custom"

        @property
        def supported_strategy(self) -> str:
            return "custom_v1"

        async def retrieve(self, query, context):
            return [_cand("custom1", "custom_v1")]

    registry = RetrieverRegistry()
    registry.register_retriever(MockCustomRetriever())
    registry.register_expander(PassthroughExpander())
    registry.register_fuser(RRFScoreFuser())
    registry.register_reranker(PassthroughReranker())
    pipe = registry.build_pipeline(RetrievalEngineConfig())
    # rebuild with custom expander from registry — build_pipeline uses defaults;
    # wire router manually for this strategy.
    pipe = RetrievalEnginePipeline(
        expander=registry.get_expander("passthrough"),
        router=StrategyRouter(registry.get_retriever),
        fuser=registry.get_fuser("rrf"),
        reranker=registry.get_reranker("passthrough"),
        budget_enforcer=BudgetEnforcer(),
        tracer_factory=RetrievalTracer,
        config=RetrievalEngineConfig(),
    )
    result = await pipe.execute(plan_builder(["custom_v1"]))
    assert any(c.chunk_id == "custom1" for c in result.candidates)


@pytest.mark.asyncio
async def test_unregistered_strategy_skipped():
    ret = mock_retriever("semantic", [_cand("c1", "semantic")])
    pipe = _pipeline(retrievers={"semantic": ret})
    result = await pipe.execute(plan_builder(["semantic", "nope"]))
    skipped = [s for s in result.trace.steps if s.skip_reason == "retriever_not_found"]
    assert skipped
    assert skipped[0].skipped is True


@pytest.mark.asyncio
async def test_pharmacy_hybrid_three_components():
    r1 = mock_retriever("semantic", [_cand("a", "semantic")])
    r2 = mock_retriever("keyword", [_cand("b", "keyword")])
    r3 = mock_retriever("metadata", [_cand("c", "metadata")])
    pipe = _pipeline(
        retrievers={"semantic": r1, "keyword": r2, "metadata": r3},
        config=RetrievalEngineConfig(
            hybrid_components=["semantic", "keyword", "metadata"]
        ),
    )
    result = await pipe.execute(plan_builder(["hybrid"]))
    assert len(result.trace.steps) == 3
    assert result.metadata.hybrid_components_used == (
        "semantic",
        "keyword",
        "metadata",
    )


@pytest.mark.asyncio
async def test_graph_not_in_default_registry():
    registry = RetrieverRegistry()
    registry.register_defaults()
    assert registry.get_retriever("graph") is None
    pipe = RetrievalEnginePipeline(
        expander=registry.get_expander("passthrough"),
        router=StrategyRouter(registry.get_retriever),
        fuser=registry.get_fuser("rrf"),
        reranker=registry.get_reranker("passthrough"),
        budget_enforcer=BudgetEnforcer(),
        tracer_factory=RetrievalTracer,
        config=RetrievalEngineConfig(),
    )
    result = await pipe.execute(plan_builder(["graph"]))
    assert result.trace.steps[0].skip_reason == "retriever_not_found"


@pytest.mark.asyncio
async def test_sc004_new_strategy_extensibility():
    class MockNewStrategyRetriever(IRetriever):
        def __init__(self) -> None:
            self.called = False

        @property
        def retriever_id(self) -> str:
            return "new_v2"

        @property
        def supported_strategy(self) -> str:
            return "new_strategy_v2"

        async def retrieve(self, query, context):
            self.called = True
            return [_cand("n1", "new_strategy_v2")]

    registry = RetrieverRegistry()
    mock = MockNewStrategyRetriever()
    registry.register_retriever(mock)
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
    result = await pipe.execute(plan_builder(["new_strategy_v2"]))
    assert mock.called is True
    assert result.candidates
    assert result.schema_version == "1.0.0"
