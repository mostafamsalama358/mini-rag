"""Unit tests for query expanders."""

from __future__ import annotations

import pytest

from core.retrieval_engine.budget.enforcer import BudgetEnforcer
from core.retrieval_engine.expansion.passthrough import PassthroughExpander
from core.retrieval_engine.fusion.rrf import RRFScoreFuser
from core.retrieval_engine.interfaces import IQueryExpander
from core.retrieval_engine.models import (
    ExpansionContext,
    ExpansionResult,
    RawCandidate,
    RetrievalEngineConfig,
    SourceRef,
)
from core.retrieval_engine.pipeline import RetrievalEnginePipeline
from core.retrieval_engine.reranking.passthrough import PassthroughReranker
from core.retrieval_engine.router import StrategyRouter
from core.retrieval_engine.tracing.tracer import RetrievalTracer
from tests.unit.core.retrieval_engine.conftest import mock_retriever, plan_builder


def test_passthrough_expander():
    exp = PassthroughExpander()
    ctx = ExpansionContext(query_text="hello world")
    result = exp.expand(ctx)
    assert result.variants == ("hello world",)
    assert result.expansion_type == "passthrough"
    assert result.metadata == {}
    assert len(result.variants) == 1


def test_mock_three_variant_expander():
    class _Mock(IQueryExpander):
        @property
        def expander_id(self) -> str:
            return "mock"

        @property
        def expansion_type(self) -> str:
            return "mock"

        def expand(self, context: ExpansionContext) -> ExpansionResult:
            return ExpansionResult(
                variants=("v0", "v1", "v2"),
                expansion_type="mock",
            )

    result = _Mock().expand(ExpansionContext(query_text="q"))
    assert result.variants == ("v0", "v1", "v2")


@pytest.mark.asyncio
async def test_max_expander_variants_cap():
    class _Five(IQueryExpander):
        @property
        def expander_id(self) -> str:
            return "five"

        @property
        def expansion_type(self) -> str:
            return "mock"

        def expand(self, context: ExpansionContext) -> ExpansionResult:
            return ExpansionResult(
                variants=("a", "b", "c", "d", "e"),
                expansion_type="mock",
            )

    ret = mock_retriever(
        "semantic",
        [
            RawCandidate(
                chunk_id="c1",
                document_id="d1",
                raw_score=0.9,
                retriever_id="mock_semantic",
                strategy="semantic",
                expander_variant_id="v0",
                content_excerpt="x",
                source_ref=SourceRef(document_id="d1", chunk_id="c1"),
            )
        ],
    )
    pipeline = RetrievalEnginePipeline(
        expander=_Five(),
        router=StrategyRouter(lambda s: ret if s == "semantic" else None),
        fuser=RRFScoreFuser(),
        reranker=PassthroughReranker(),
        budget_enforcer=BudgetEnforcer(),
        tracer_factory=RetrievalTracer,
        config=RetrievalEngineConfig(max_expander_variants=3),
    )
    plan = plan_builder(["semantic"])
    result = await pipeline.execute(plan)
    assert len(result.trace.steps) == 3
