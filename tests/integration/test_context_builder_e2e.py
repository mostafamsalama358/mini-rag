"""End-to-end integration tests for Context Builder."""

from __future__ import annotations

import pytest

from core.context_builder.config import BudgetReservations, ContextBuilderConfig
from core.context_builder.registry import ContextBuilderRegistry
from tests.unit.core.context_builder.conftest import (
    build_pack_with_mix,
    build_synthetic_pack,
    make_empty_pack,
    make_item,
    make_pack,
)


@pytest.fixture
def pipeline_config() -> ContextBuilderConfig:
    return ContextBuilderConfig(
        total_context_window=8000,
        reservations=BudgetReservations(system_prompt=500, question=200, output=1000),
        compression_enabled=True,
        compressibility_threshold=0.7,
        final_dedup_enabled=True,
    )


@pytest.fixture
def pipeline(pipeline_config):
    return ContextBuilderRegistry.build(pipeline_config)


@pytest.mark.asyncio
async def test_scenario_1_budget_compliance(pipeline, pipeline_config):
    pack = build_synthetic_pack(n_items=20, tokens_per_item=600)
    ctx = await pipeline.build(pack, pipeline_config)
    assert ctx.token_count <= pipeline_config.available_budget
    assert len(ctx.ordered_blocks) < 20
    assert len(ctx.ordered_blocks) == len(ctx.citation_map)
    assert ctx.metadata.items_dropped > 0
    assert ctx.metadata.budget_used == ctx.token_count


@pytest.mark.asyncio
async def test_scenario_2_compressibility_ordering(pipeline, pipeline_config):
    pack = build_pack_with_mix(
        high_compress_count=5,
        high_score=0.9,
        low_compress_count=5,
        low_score=0.1,
        tokens_per_item=400,
    )
    tight_config = pipeline_config.model_copy(update={"total_context_window": 12000})
    ctx = await pipeline.build(pack, tight_config)
    low_ids = {i.item_id for i in pack.items if i.compressibility_score < 0.5}
    included = {b.item_id for b in ctx.ordered_blocks}
    assert low_ids.issubset(included)


@pytest.mark.asyncio
async def test_scenario_3_conflict_detection(pipeline, pipeline_config):
    item_a = make_item(
        entity_tags=["metformin"],
        text="Patients received metformin 500mg twice daily.",
    )
    item_b = make_item(
        chunk_id="chunk2",
        entity_tags=["metformin"],
        text="The dosage of metformin was 1000mg per day.",
    )
    pack = make_pack([item_a, item_b])
    ctx = await pipeline.build(pack, pipeline_config)
    assert len(ctx.conflicts) == 1
    cg = ctx.conflicts[0]
    assert cg.entity_tag == "metformin"
    assert set(cg.item_ids) == {item_a.item_id, item_b.item_id}


@pytest.mark.asyncio
async def test_scenario_4_document_ordering(pipeline, pipeline_config):
    items = [
        make_item(
            doc_id="docA",
            section_path=["Results"],
            relevance_score=0.5,
            text="Document A results section content.",
            chunk_id="c1",
        ),
        make_item(
            doc_id="docA",
            section_path=["Introduction"],
            relevance_score=0.9,
            chunk_id="c2",
            text="Document A introduction section content.",
        ),
        make_item(
            doc_id="docB",
            section_path=["Summary"],
            relevance_score=0.7,
            chunk_id="c3",
            text="Document B summary section content.",
        ),
    ]
    pack = make_pack(items)
    ctx = await pipeline.build(pack, pipeline_config)
    blocks = ctx.ordered_blocks
    doc_ids = [b.document_id for b in blocks]
    assert doc_ids.index("docA") < doc_ids.index("docB")
    doc_a_blocks = [b for b in blocks if b.document_id == "docA"]
    assert doc_a_blocks[0].section_path == "Introduction"
    assert doc_a_blocks[1].section_path == "Results"


@pytest.mark.asyncio
async def test_scenario_5_zero_broken_citations(pipeline, pipeline_config):
    contexts = []
    for factory in (
        lambda: build_synthetic_pack(n_items=10, tokens_per_item=200),
        lambda: build_pack_with_mix(
            high_compress_count=3,
            high_score=0.9,
            low_compress_count=3,
            low_score=0.1,
            tokens_per_item=100,
        ),
        lambda: make_pack(
            [
                make_item(entity_tags=["metformin"], text="metformin 500mg"),
                make_item(chunk_id="c2", entity_tags=["metformin"], text="metformin 1000mg"),
            ]
        ),
        lambda: make_pack(
            [
                make_item(doc_id="docA", section_path=["Intro"]),
                make_item(doc_id="docB", section_path=["Summary"], chunk_id="c2"),
            ]
        ),
    ):
        ctx = await pipeline.build(factory(), pipeline_config)
        contexts.append(ctx)

    for ctx in contexts:
        block_ids = {b.item_id for b in ctx.ordered_blocks}
        citation_ids = set(ctx.citation_map.keys())
        assert block_ids == citation_ids


@pytest.mark.asyncio
async def test_scenario_6_empty_pack(pipeline, pipeline_config):
    ctx = await pipeline.build(make_empty_pack(), pipeline_config)
    assert ctx.token_count == 0
    assert ctx.ordered_blocks == []
    assert ctx.citation_map == {}
    assert ctx.conflicts == []
    assert ctx.metadata.items_included == 0
