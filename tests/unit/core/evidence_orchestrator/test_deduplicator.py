"""Unit tests for EmbeddingDeduplicator."""

from __future__ import annotations

import pytest

from core.evidence_orchestrator.collection.retrieval_result_collector import (
    RetrievalResultCollector,
)
from core.evidence_orchestrator.config import EvidenceOrchestratorConfig
from core.evidence_orchestrator.deduplication.embedding_deduplicator import (
    EmbeddingDeduplicator,
)
from tests.unit.core.evidence_orchestrator.conftest import (
    MockEmbeddingProvider,
    make_candidate,
    make_result,
)


async def _collect(result, plan, config):
    return await RetrievalResultCollector().collect(result, plan, config)


@pytest.mark.asyncio
async def test_exact_duplicate_merge(minimal_retrieval_plan, default_config):
    c1 = make_candidate(chunk_id="same", score=0.9, rank=1)
    c2 = make_candidate(chunk_id="same", score=0.7, rank=2)
    result = make_result([c1, c2], strategies=("semantic", "keyword"))
    collected = await _collect(result, minimal_retrieval_plan, default_config)
    deduped = await EmbeddingDeduplicator().deduplicate(collected, default_config)
    assert len(deduped) == 1
    assert deduped[0].candidate.score == 0.9
    assert len(deduped[0].contributing_sources) == 2


@pytest.mark.asyncio
async def test_zero_duplicates_passthrough(minimal_retrieval_plan, default_config):
    c1 = make_candidate(chunk_id="c1", content_excerpt="unique content alpha")
    c2 = make_candidate(chunk_id="c2", content_excerpt="unique content beta", rank=2)
    result = make_result([c1, c2])
    collected = await _collect(result, minimal_retrieval_plan, default_config)
    deduped = await EmbeddingDeduplicator().deduplicate(collected, default_config)
    assert len(deduped) == 2


@pytest.mark.asyncio
async def test_near_duplicate_cosine(minimal_retrieval_plan, default_config):
    text = "identical near duplicate content"
    c1 = make_candidate(chunk_id="c1", content_excerpt=text)
    c2 = make_candidate(chunk_id="c2", content_excerpt=text, rank=2)
    result = make_result([c1, c2])
    collected = await _collect(result, minimal_retrieval_plan, default_config)
    provider = MockEmbeddingProvider(vectors={text: [1.0, 0.0, 0.0]})
    deduped = await EmbeddingDeduplicator(embedding_provider=provider).deduplicate(
        collected, default_config
    )
    assert len(deduped) == 1


@pytest.mark.asyncio
async def test_character_ngram_fallback(minimal_retrieval_plan):
    config = EvidenceOrchestratorConfig(dedup_near_batch_limit=200)
    text_a = "near duplicate alpha content xyz"
    text_b = "near duplicate alpha content xyz!"
    candidates = [
        make_candidate(
            chunk_id=f"c{i}",
            content_excerpt=text_a if i % 2 == 0 else text_b,
            rank=i + 1,
        )
        for i in range(201)
    ]
    result = make_result(candidates)
    collected = await _collect(result, minimal_retrieval_plan, config)
    dedup = EmbeddingDeduplicator(embedding_provider=MockEmbeddingProvider())
    deduped = await dedup.deduplicate(collected, config)
    assert dedup.last_method_used == "character_ngram"
    assert len(deduped) < len(collected)


@pytest.mark.asyncio
async def test_embedding_unavailable_fallback(minimal_retrieval_plan, default_config):
    text = "shared fallback text"
    c1 = make_candidate(chunk_id="c1", content_excerpt=text)
    c2 = make_candidate(chunk_id="c2", content_excerpt=text, rank=2)
    result = make_result([c1, c2])
    collected = await _collect(result, minimal_retrieval_plan, default_config)
    provider = MockEmbeddingProvider(fail=True)
    dedup = EmbeddingDeduplicator(embedding_provider=provider)
    deduped = await dedup.deduplicate(collected, default_config)
    assert dedup.last_method_used == "character_ngram"
    assert len(deduped) == 1


@pytest.mark.asyncio
async def test_dedup_near_disabled(minimal_retrieval_plan):
    config = EvidenceOrchestratorConfig(dedup_near_enabled=False)
    text = "same text different ids"
    c1 = make_candidate(chunk_id="c1", content_excerpt=text)
    c2 = make_candidate(chunk_id="c2", content_excerpt=text, rank=2)
    result = make_result([c1, c2])
    collected = await _collect(result, minimal_retrieval_plan, config)
    dedup = EmbeddingDeduplicator(embedding_provider=MockEmbeddingProvider())
    deduped = await dedup.deduplicate(collected, config)
    assert len(deduped) == 2
    assert dedup.last_method_used == "exact_only"
