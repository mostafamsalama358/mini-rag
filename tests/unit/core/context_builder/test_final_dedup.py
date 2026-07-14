"""Unit tests for FinalPassDeduplicator."""

from __future__ import annotations

from core.context_builder.config import ContextBuilderConfig
from core.context_builder.dedup.text_similarity_dedup import FinalPassDeduplicator
from tests.unit.core.context_builder.conftest import make_item


def test_high_similarity_drops_lower_ranked():
    text = "Nearly identical evidence paragraph about aspirin dosage guidance."
    high = make_item(
        chunk_id="high",
        text=text,
        relevance_score=0.9,
    )
    low = make_item(
        chunk_id="low",
        text=text + " extra",
        relevance_score=0.4,
    )
    dedup = FinalPassDeduplicator()
    kept, removed = dedup.deduplicate([high, low], ContextBuilderConfig())
    ids = {item.item_id for item in kept}
    assert high.item_id in ids
    assert low.item_id not in ids
    assert removed == 1


def test_low_similarity_retains_both():
    a = make_item(chunk_id="a", text="Completely different topic alpha.", relevance_score=0.9)
    b = make_item(chunk_id="b", text="Unrelated content beta gamma.", relevance_score=0.5)
    dedup = FinalPassDeduplicator()
    kept, removed = dedup.deduplicate([a, b], ContextBuilderConfig())
    assert len(kept) == 2
    assert removed == 0


def test_final_dedup_disabled_passes_through():
    text = "Duplicate text " * 10
    a = make_item(chunk_id="a", text=text, relevance_score=0.9)
    b = make_item(chunk_id="b", text=text, relevance_score=0.1)
    config = ContextBuilderConfig(final_dedup_enabled=False)
    kept, removed = FinalPassDeduplicator().deduplicate([a, b], config)
    assert len(kept) == 2
    assert removed == 0


def test_max_pairs_cap_leaves_remainder():
    items = [
        make_item(
            chunk_id=f"c{i}",
            text=f"shared duplicate content block number {i % 2}",
            relevance_score=1.0 - (i * 0.01),
        )
        for i in range(10)
    ]
    config = ContextBuilderConfig(final_dedup_max_pairs=2)
    kept, _ = FinalPassDeduplicator().deduplicate(items, config)
    assert len(kept) >= 2
