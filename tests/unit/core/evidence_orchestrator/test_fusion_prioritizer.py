"""Unit tests for FusionPrioritizer."""

from __future__ import annotations

import pytest

from core.evidence_orchestrator.models import Citation, EvidenceItem, EvidenceItemSource
from core.evidence_orchestrator.prioritization.fusion_prioritizer import FusionPrioritizer
from core.evidence_orchestrator.models import compute_item_id


def _item(
    *,
    chunk_id: str,
    text: str,
    score: float,
    chunk_index: int | None = None,
) -> EvidenceItem:
    return EvidenceItem(
        item_id=compute_item_id(chunk_id, "doc1"),
        doc_id="doc1",
        chunk_id=chunk_id,
        citation=Citation(
            document_id="doc1",
            chunk_id=chunk_id,
            retrieval_score=score,
            score_source="fusion",
            chunk_index=chunk_index,
        ),
        text=text,
        relevance_score=score,
        sources=[EvidenceItemSource(strategy_id="semantic", raw_score=score)],
    )


@pytest.mark.asyncio
async def test_entity_boost(plan_with_entities, default_config):
    item_a = _item(
        chunk_id="a",
        text="Information about aspirin and ibuprofen interactions.",
        score=0.5,
    )
    item_b = _item(chunk_id="b", text="Generic unrelated medical text.", score=0.5)
    ranked = await FusionPrioritizer().prioritize(
        [item_b, item_a], plan_with_entities, default_config
    )
    assert ranked[0].chunk_id == "a"
    assert ranked[0].relevance_score > ranked[1].relevance_score


@pytest.mark.asyncio
async def test_no_entities_retrieval_only(minimal_retrieval_plan, default_config):
    low = _item(chunk_id="low", text="alpha", score=0.2)
    high = _item(chunk_id="high", text="beta", score=0.9)
    ranked = await FusionPrioritizer().prioritize(
        [low, high], minimal_retrieval_plan, default_config
    )
    assert ranked[0].chunk_id == "high"


@pytest.mark.asyncio
async def test_recency_boost(minimal_retrieval_plan, default_config):
    older = _item(chunk_id="old", text="text", score=0.5, chunk_index=1)
    newer = _item(chunk_id="new", text="text", score=0.5, chunk_index=10)
    ranked = await FusionPrioritizer().prioritize(
        [older, newer], minimal_retrieval_plan, default_config
    )
    assert ranked[0].chunk_id == "new"


@pytest.mark.asyncio
async def test_single_item(minimal_retrieval_plan, default_config):
    item = _item(chunk_id="only", text="solo", score=0.7)
    ranked = await FusionPrioritizer().prioritize(
        [item], minimal_retrieval_plan, default_config
    )
    assert len(ranked) == 1
    assert ranked[0].relevance_score > 0


@pytest.mark.asyncio
async def test_empty_input(minimal_retrieval_plan, default_config):
    ranked = await FusionPrioritizer().prioritize(
        [], minimal_retrieval_plan, default_config
    )
    assert ranked == []


@pytest.mark.asyncio
async def test_sorted_descending(plan_with_entities, default_config):
    items = [
        _item(chunk_id="m", text="middle aspirin", score=0.5),
        _item(chunk_id="h", text="high aspirin ibuprofen", score=0.8),
        _item(chunk_id="l", text="low", score=0.1),
    ]
    ranked = await FusionPrioritizer().prioritize(
        items, plan_with_entities, default_config
    )
    scores = [i.relevance_score for i in ranked]
    assert scores == sorted(scores, reverse=True)
