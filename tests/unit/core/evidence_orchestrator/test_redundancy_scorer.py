"""Unit tests for RedundancyScorer."""

from __future__ import annotations

import pytest

from core.evidence_orchestrator.compression.redundancy_scorer import RedundancyScorer
from core.evidence_orchestrator.config import CompressibilityWeights, EvidenceOrchestratorConfig
from core.evidence_orchestrator.models import Citation, EvidenceItem, EvidenceItemSource
from core.evidence_orchestrator.models import compute_item_id


def _item(*, chunk_id: str, text: str, relevance: float) -> EvidenceItem:
    return EvidenceItem(
        item_id=compute_item_id(chunk_id, "doc1"),
        doc_id="doc1",
        chunk_id=chunk_id,
        citation=Citation(
            document_id="doc1",
            chunk_id=chunk_id,
            retrieval_score=relevance,
            score_source="fusion",
        ),
        text=text,
        relevance_score=relevance,
        sources=[EvidenceItemSource(strategy_id="semantic", raw_score=relevance)],
    )


@pytest.mark.asyncio
async def test_unique_high_relevance_low_compressibility(default_config):
    item = _item(
        chunk_id="unique",
        text="Completely unique high value evidence content.",
        relevance=0.95,
    )
    scored = await RedundancyScorer().score([item], default_config)
    assert scored[0].compressibility_score < 0.3


@pytest.mark.asyncio
async def test_near_duplicate_high_compressibility(default_config):
    base = "alpha beta gamma delta epsilon zeta eta theta iota kappa " * 5
    near = base + base[: int(len(base) * 0.9)]
    high = _item(chunk_id="h", text=base, relevance=0.9)
    near_item = _item(chunk_id="n", text=near, relevance=0.7)
    scored = await RedundancyScorer().score([high, near_item], default_config)
    by_id = {i.chunk_id: i for i in scored}
    assert by_id["n"].compressibility_score > 0.7


@pytest.mark.asyncio
async def test_low_relevance_unique(default_config):
    item = _item(
        chunk_id="low",
        text="Unique but low relevance content here.",
        relevance=0.1,
    )
    scored = await RedundancyScorer().score([item], default_config)
    assert scored[0].compressibility_score > 0.3


@pytest.mark.asyncio
async def test_single_item(default_config):
    item = _item(chunk_id="solo", text="single item", relevance=0.5)
    scored = await RedundancyScorer().score([item], default_config)
    expected = 0.4 * (1.0 - 0.5)
    assert scored[0].compressibility_score == pytest.approx(expected, abs=0.01)


@pytest.mark.asyncio
async def test_empty_input(default_config):
    scored = await RedundancyScorer().score([], default_config)
    assert scored == []


@pytest.mark.asyncio
async def test_empty_text_fallback(default_config):
    good = _item(chunk_id="good", text="valid text content", relevance=0.8)
    bad = _item(chunk_id="bad", text=" ", relevance=0.8)
    scored = await RedundancyScorer().score([good, bad], default_config)
    by_id = {i.chunk_id: i for i in scored}
    assert by_id["bad"].compressibility_score == 0.5


@pytest.mark.asyncio
async def test_weights_override():
    config = EvidenceOrchestratorConfig(
        compressibility_weights=CompressibilityWeights(
            redundancy=0.8, relevance_inverse=0.2
        )
    )
    base = "shared content for weight override test case"
    a = _item(chunk_id="a", text=base, relevance=0.9)
    b = _item(chunk_id="b", text=base, relevance=0.4)
    scored = await RedundancyScorer().score([a, b], config)
    assert scored[1].compressibility_score > 0.5
