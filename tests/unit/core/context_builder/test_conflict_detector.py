"""Unit tests for EntityTagConflictDetector."""

from __future__ import annotations

import pytest

from core.context_builder.conflict.entity_tag_detector import EntityTagConflictDetector
from core.context_builder.config import ContextBuilderConfig
from tests.unit.core.context_builder.conftest import make_item


@pytest.fixture
def detector() -> EntityTagConflictDetector:
    return EntityTagConflictDetector()


@pytest.fixture
def config() -> ContextBuilderConfig:
    return ContextBuilderConfig()


@pytest.mark.asyncio
async def test_numeric_conflict_produces_one_group(detector, config):
    item_a = make_item(
        entity_tags=["metformin"],
        text="Patients received metformin 500mg twice daily.",
    )
    item_b = make_item(
        chunk_id="chunk2",
        entity_tags=["metformin"],
        text="The dosage of metformin was 1000mg per day.",
    )
    groups = await detector.detect([item_a, item_b], config)
    assert len(groups) == 1
    assert groups[0].entity_tag == "metformin"
    assert set(groups[0].item_ids) == {item_a.item_id, item_b.item_id}


@pytest.mark.asyncio
async def test_no_shared_entity_tag_returns_empty(detector, config):
    item_a = make_item(entity_tags=["aspirin"], text="aspirin 100mg")
    item_b = make_item(chunk_id="c2", entity_tags=["ibuprofen"], text="ibuprofen 200mg")
    groups = await detector.detect([item_a, item_b], config)
    assert groups == []


@pytest.mark.asyncio
async def test_three_items_same_tag_merged_not_pairs(detector, config):
    items = [
        make_item(
            chunk_id=f"c{i}",
            entity_tags=["metformin"],
            text=f"metformin dose {500 + (i * 100)}mg",
        )
        for i in range(3)
    ]
    groups = await detector.detect(items, config)
    assert len(groups) == 1
    assert len(groups[0].item_ids) == 3


@pytest.mark.asyncio
async def test_detector_failure_returns_empty(monkeypatch, detector, config):
    def _boom(_text, _tag):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "core.context_builder.conflict.entity_tag_detector._extract_numeric_values",
        _boom,
    )
    item_a = make_item(entity_tags=["x"], text="x 10")
    item_b = make_item(chunk_id="c2", entity_tags=["x"], text="x 20")
    groups = await detector.detect([item_a, item_b], config)
    assert groups == []


@pytest.mark.asyncio
async def test_conflict_item_ids_present_in_input(detector, config):
    item_a = make_item(entity_tags=["price"], text="price is 10 for product price")
    item_b = make_item(chunk_id="c2", entity_tags=["price"], text="price is 20 for product price")
    input_ids = {item_a.item_id, item_b.item_id}
    groups = await detector.detect([item_a, item_b], config)
    for group in groups:
        assert set(group.item_ids).issubset(input_ids)
