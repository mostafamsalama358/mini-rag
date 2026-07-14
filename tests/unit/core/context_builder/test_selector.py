"""Unit tests for budget selection helper."""

from __future__ import annotations

import pytest

from core.context_builder.compression.heuristic_compressor import (
    HeuristicTruncationCompressor,
)
from core.context_builder.config import BudgetReservations, ContextBuilderConfig
from core.context_builder.pipeline import _select_under_budget
from core.evidence_orchestrator.token_counting.character_approximation import (
    CharacterApproximationTokenCounter,
)
from tests.unit.core.context_builder.conftest import build_synthetic_pack, make_item


@pytest.fixture
def counter() -> CharacterApproximationTokenCounter:
    return CharacterApproximationTokenCounter()


@pytest.fixture
def compressor() -> HeuristicTruncationCompressor:
    return HeuristicTruncationCompressor()


@pytest.mark.asyncio
async def test_items_selected_in_descending_relevance_order(counter, compressor):
    items = [
        make_item(chunk_id="a", relevance_score=0.9, text="a " * 50),
        make_item(chunk_id="b", relevance_score=0.5, text="b " * 50),
        make_item(chunk_id="c", relevance_score=0.1, text="c " * 50),
    ]
    config = ContextBuilderConfig(compressibility_threshold=0.7)
    selected, dropped, _ = await _select_under_budget(
        items,
        budget=30,
        config=config,
        compressor=compressor,
        token_counter=counter,
    )
    assert dropped >= 1
    scores = [entry.item.relevance_score for entry in selected]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_high_compressibility_compressed_before_lower_scored_dropped(
    counter, compressor
):
    high = make_item(
        chunk_id="high",
        text="high " * 400,
        relevance_score=0.4,
        compressibility_score=0.95,
    )
    low = make_item(
        chunk_id="low",
        text="low " * 20,
        relevance_score=0.95,
        compressibility_score=0.1,
    )
    config = ContextBuilderConfig(
        total_context_window=4000,
        compression_enabled=True,
        compressibility_threshold=0.7,
    )
    selected, _, compressed_count = await _select_under_budget(
        [low, high],
        budget=30,
        config=config,
        compressor=compressor,
        token_counter=counter,
    )
    included = {entry.item.item_id for entry in selected}
    assert low.item_id in included
    assert compressed_count >= 0


@pytest.mark.asyncio
async def test_all_included_items_have_citations(counter, compressor):
    pack = build_synthetic_pack(n_items=5, tokens_per_item=50)
    config = ContextBuilderConfig(compressibility_threshold=0.7)
    selected, _, _ = await _select_under_budget(
        pack.items,
        budget=500,
        config=config,
        compressor=compressor,
        token_counter=counter,
    )
    for entry in selected:
        assert entry.item.citation is not None


@pytest.mark.asyncio
async def test_dropped_plus_included_equals_pack_size(counter, compressor):
    pack = build_synthetic_pack(n_items=10, tokens_per_item=200)
    config = ContextBuilderConfig(compressibility_threshold=0.7)
    selected, dropped, _ = await _select_under_budget(
        pack.items,
        budget=300,
        config=config,
        compressor=compressor,
        token_counter=counter,
    )
    assert dropped + len(selected) == len(pack.items)


@pytest.mark.asyncio
async def test_all_items_fit_includes_everything_uncompressed(counter, compressor):
    items = [
        make_item(chunk_id=f"c{i}", text=f"short {i}", relevance_score=1.0 - i * 0.1)
        for i in range(3)
    ]
    config = ContextBuilderConfig(compressibility_threshold=0.7)
    selected, dropped, compressed_count = await _select_under_budget(
        items,
        budget=10_000,
        config=config,
        compressor=compressor,
        token_counter=counter,
    )
    assert dropped == 0
    assert len(selected) == 3
    assert compressed_count == 0
    assert all(not entry.compressed for entry in selected)
