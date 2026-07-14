"""Shared fixtures for Evidence Orchestrator unit tests."""

from __future__ import annotations

from typing import Any

import pytest

from core.evidence_orchestrator.config import EvidenceOrchestratorConfig
from core.evidence_orchestrator.interfaces import IChunkReader, IEmbeddingProvider
from core.retrieval_engine.models import (
    RetrievalExecutionMetadata,
    RetrievalResult,
    RetrievalStepTrace,
    RetrievalTrace,
    RetrievedCandidate,
    SourceRef,
    compute_result_id,
)
from core.retrieval_planner.models import (
    OutputShape,
    QueryIntent,
    ResolvedEntity,
    RetrievalConstraints,
    RetrievalLimits,
    RetrievalPlan,
    RetrievalPlanMetadata,
    compute_entity_id,
)


def _plan_id() -> str:
    return "rp_" + "a" * 16


@pytest.fixture
def default_config() -> EvidenceOrchestratorConfig:
    return EvidenceOrchestratorConfig()


@pytest.fixture
def minimal_retrieval_plan() -> RetrievalPlan:
    return RetrievalPlan(
        canonical_query="test query",
        intent=QueryIntent(category="factual", confidence=0.9),
        entities=(),
        filters=(),
        retrieval_strategies=("semantic",),
        retrieval_limits=RetrievalLimits(
            max_evidence_units=5,
            max_candidates=20,
            scope="narrow",
        ),
        retrieval_constraints=RetrievalConstraints(citation_required=True),
        execution_hints=None,
        output_shape=OutputShape(
            shape_type="single_fact", max_items=None, structured=False
        ),
        clarification_required=False,
        clarification_question=None,
        planner_confidence=0.9,
        diagnostics=None,
        metadata=RetrievalPlanMetadata(
            plan_id=_plan_id(),
            planner_version="1.0.0",
            schema_version="1.0.0",
            config_hash="deadbeef",
            created_at="2026-07-14T00:00:00Z",
        ),
    )


def make_candidate(
    *,
    chunk_id: str = "chunk1",
    document_id: str = "doc1",
    score: float = 0.9,
    content_excerpt: str = "Sample evidence text about aspirin.",
    strategy_index: int = 0,
    source_ref: SourceRef | None = None,
    rank: int = 1,
) -> RetrievedCandidate:
    return RetrievedCandidate(
        chunk_id=chunk_id,
        document_id=document_id,
        score=score,
        score_source="fusion",
        source_ref=source_ref
        or SourceRef(
            document_id=document_id,
            chunk_id=chunk_id,
            page_number=1,
            section_title="Introduction",
            chunk_index=strategy_index,
        ),
        content_excerpt=content_excerpt,
        rank=rank,
    )


def make_result(
    candidates: list[RetrievedCandidate],
    *,
    strategies: tuple[str, ...] = ("semantic",),
    plan_id: str | None = None,
) -> RetrievalResult:
    pid = plan_id or _plan_id()
    steps = tuple(
        RetrievalStepTrace(
            step_index=i,
            strategy=strategies[i % len(strategies)],
            expander_variant_id="v0",
            retriever_id=f"mock_{strategies[i % len(strategies)]}",
            raw_count=1,
        )
        for i in range(len(candidates))
    )
    result_id = compute_result_id(pid, strategies, "rrf", "passthrough")
    return RetrievalResult(
        result_id=result_id,
        plan_id=pid,
        candidates=tuple(candidates),
        trace=RetrievalTrace(plan_id=pid, steps=steps),
        metadata=RetrievalExecutionMetadata(
            result_id=result_id,
            plan_id=pid,
            executed_strategies=strategies,
        ),
    )


@pytest.fixture
def minimal_retrieval_result() -> RetrievalResult:
    return make_result([make_candidate()])


class MockChunkReader(IChunkReader):
    def __init__(self, chunks: dict[tuple[str, str], Any] | None = None) -> None:
        self._chunks = chunks or {}
        self.calls: list[tuple[str, str]] = []

    async def get_chunk(self, chunk_id: str, document_id: str):
        self.calls.append((chunk_id, document_id))
        return self._chunks.get((chunk_id, document_id))


@pytest.fixture
def mock_chunk_reader() -> MockChunkReader:
    return MockChunkReader()


class MockEmbeddingProvider(IEmbeddingProvider):
    def __init__(
        self,
        *,
        vectors: dict[str, list[float]] | None = None,
        fail: bool = False,
    ) -> None:
        self._vectors = vectors or {}
        self._fail = fail
        self.calls: list[list[str]] = []

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        if self._fail:
            raise RuntimeError("embedding unavailable")
        result: list[list[float]] = []
        for text in texts:
            if text in self._vectors:
                result.append(self._vectors[text])
            else:
                result.append([float(len(text)), float(hash(text) % 100)])
        return result


@pytest.fixture
def mock_embedding_provider() -> MockEmbeddingProvider:
    return MockEmbeddingProvider()


@pytest.fixture
def plan_with_entities(minimal_retrieval_plan: RetrievalPlan) -> RetrievalPlan:
    entities = (
        ResolvedEntity(
            entity_id=compute_entity_id("aspirin", "drug"),
            raw_text="aspirin",
            canonical_form="aspirin",
            entity_type="drug",
        ),
        ResolvedEntity(
            entity_id=compute_entity_id("ibuprofen", "drug"),
            raw_text="ibuprofen",
            canonical_form="ibuprofen",
            entity_type="drug",
        ),
    )
    return minimal_retrieval_plan.model_copy(update={"entities": entities})
