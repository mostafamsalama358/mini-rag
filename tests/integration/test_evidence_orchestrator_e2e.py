"""End-to-end integration tests for Evidence Orchestrator."""

from __future__ import annotations

import pytest

from core.chunking.models import Chunk, ChunkIdentity, ChunkRelationships
from core.evidence_orchestrator.registry import EvidenceOrchestratorRegistry
from core.retrieval_planner.models import ResolvedEntity, compute_entity_id
from tests.unit.core.evidence_orchestrator.conftest import (
    MockChunkReader,
    MockEmbeddingProvider,
    make_candidate,
    make_result,
)


def _chunk(chunk_id: str, text: str, **relationships) -> Chunk:
    return Chunk(
        text=text,
        identity=ChunkIdentity(
            chunk_id=chunk_id,
            document_id="doc1",
            strategy_id="semantic",
            source_element_ids=[chunk_id],
        ),
        relationships=ChunkRelationships(**relationships),
    )


def _build_e2e_fixtures(plan_with_entities):
    entities = (
        ResolvedEntity(
            entity_id=compute_entity_id("entity_a", "concept"),
            raw_text="entity_a",
            canonical_form="entity_a",
            entity_type="concept",
        ),
        ResolvedEntity(
            entity_id=compute_entity_id("entity_b", "concept"),
            raw_text="entity_b",
            canonical_form="entity_b",
            entity_type="concept",
        ),
        ResolvedEntity(
            entity_id=compute_entity_id("entity_c", "concept"),
            raw_text="entity_c",
            canonical_form="entity_c",
            entity_type="concept",
        ),
    )
    plan = plan_with_entities.model_copy(update={"entities": entities})

    exact_dup_text = "exact duplicate chunk content"
    near_dup_text = "near duplicate shared semantic content block"
    near_variant = near_dup_text + " extra"
    unique_texts = [
        "unique evidence about entity_a and entity_b for ranking",
        "unique evidence about entity_c only",
        "another unique chunk without entities",
        "high score chunk with entity_a match",
        "medium unique chunk seven",
        "medium unique chunk eight",
        "low unique chunk nine",
        "low unique chunk ten",
    ]

    candidates = []
    rank = 1
    for _ in range(4):
        candidates.append(
            make_candidate(
                chunk_id="exact_dup",
                content_excerpt=exact_dup_text,
                score=0.85,
                rank=rank,
            )
        )
        rank += 1
    for _ in range(4):
        candidates.append(
            make_candidate(
                chunk_id="exact_dup",
                content_excerpt=exact_dup_text,
                score=0.75,
                rank=rank,
            )
        )
        rank += 1

    for i in range(2):
        candidates.append(
            make_candidate(
                chunk_id=f"near_{i}",
                content_excerpt=near_dup_text if i == 0 else near_variant,
                score=0.82,
                rank=rank,
            )
        )
        rank += 1
    for i in range(2):
        candidates.append(
            make_candidate(
                chunk_id=f"near_b_{i}",
                content_excerpt=near_dup_text if i == 0 else near_variant,
                score=0.78,
                rank=rank,
            )
        )
        rank += 1

    for i, text in enumerate(unique_texts):
        score = 0.95 if i == 3 else 0.6 - (i * 0.02)
        candidates.append(
            make_candidate(
                chunk_id=f"unique_{i}",
                content_excerpt=text,
                score=score,
                rank=rank,
            )
        )
        rank += 1

    result = make_result(candidates, strategies=("semantic", "keyword"))
    embedding = MockEmbeddingProvider(
        vectors={
            near_dup_text: [1.0, 0.0, 0.0],
            near_variant: [0.99, 0.01, 0.0],
        }
    )
    reader = MockChunkReader(
        {
            ("unique_3", "doc1"): _chunk(
                "unique_3",
                unique_texts[3],
                previous_chunk_id="prev_high",
            ),
            ("prev_high", "doc1"): _chunk("prev_high", "PREV_HIGH"),
            ("unique_0", "doc1"): _chunk(
                "unique_0",
                unique_texts[0],
                next_chunk_id="next_high",
            ),
            ("next_high", "doc1"): _chunk("next_high", "NEXT_HIGH"),
        }
    )
    return plan, result, embedding, reader


@pytest.mark.asyncio
async def test_e2e_pipeline(plan_with_entities, default_config):
    plan, result, embedding, reader = _build_e2e_fixtures(plan_with_entities)
    orchestrator = EvidenceOrchestratorRegistry(
        embedding_provider=embedding,
        chunk_reader=reader,
    ).build_orchestrator()
    pack = await orchestrator.orchestrate(result, plan, default_config)

    assert len(pack.items) <= 12
    assert pack.raw_candidate_count == 20
    assert pack.token_reduction_ratio is not None
    assert pack.token_reduction_ratio <= 0.85
    assert pack.schema_version == "1.0.0"

    scores = [item.relevance_score for item in pack.items]
    assert scores == sorted(scores, reverse=True)

    for item in pack.items:
        assert item.citation is not None
        assert item.text
        assert item.sources
        assert item.item_id.startswith("ei_")

    entity_rich = next(i for i in pack.items if "entity_a" in i.text)
    entity_poor_candidates = [
        i for i in pack.items if i.text.startswith("low unique")
    ]
    if not entity_poor_candidates:
        entity_poor = min(pack.items, key=lambda i: i.relevance_score)
    else:
        entity_poor = entity_poor_candidates[0]
    assert entity_rich.relevance_score >= entity_poor.relevance_score


@pytest.mark.benchmark(group="orchestrate")
def test_pipeline_latency_benchmark(
    benchmark, plan_with_entities, default_config
):
    pytest.importorskip("pytest_benchmark")
    plan, result, embedding, reader = _build_e2e_fixtures(plan_with_entities)
    orchestrator = EvidenceOrchestratorRegistry(
        embedding_provider=embedding,
        chunk_reader=reader,
    ).build_orchestrator()

    candidates = []
    text = "benchmark duplicate content"
    for i in range(100):
        candidates.append(
            make_candidate(
                chunk_id=f"bench_{i // 2}",
                content_excerpt=text,
                score=0.5 + (i % 10) * 0.01,
                rank=i + 1,
            )
        )
    bench_result = make_result(candidates, strategies=("semantic", "keyword"))

    import asyncio

    def _run_sync():
        return asyncio.run(
            orchestrator.orchestrate(bench_result, plan, default_config)
        )

    pack = benchmark.pedantic(_run_sync, rounds=20, iterations=1)
    assert pack.raw_candidate_count == 100
