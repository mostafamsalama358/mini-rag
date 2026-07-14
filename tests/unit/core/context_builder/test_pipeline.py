"""Unit tests for ContextBuilderPipeline."""

from __future__ import annotations

import asyncio
import statistics
import time

import pytest

from core.context_builder.config import BudgetReservations, ContextBuilderConfig
from core.context_builder.errors import (
    CitationIntegrityError,
    EmptyBudgetError,
    EvidencePackVersionError,
)
from core.context_builder.interfaces import (
    IConflictDetector,
    IContextCompressor,
    IContextStitcher,
    ITokenBudgetAllocator,
)
from core.context_builder.models import ConflictGroup, ContextBlock
from core.context_builder.pipeline import ContextBuilderPipeline, _assert_citation_integrity
from core.context_builder.registry import ContextBuilderRegistry
from core.evidence_orchestrator.token_counting.character_approximation import (
    CharacterApproximationTokenCounter,
)
from tests.unit.core.context_builder.conftest import (
    build_synthetic_pack,
    make_empty_pack,
    make_item,
    make_pack,
)


class MockBudgetAllocator(ITokenBudgetAllocator):
    def __init__(self, budget: int) -> None:
        self._budget = budget

    def allocate(self, config: ContextBuilderConfig) -> int:
        _ = config
        return self._budget


class MockCompressor(IContextCompressor):
    async def compress(self, item, target_tokens, token_counter):
        text = item.text[: max(1, target_tokens * 4)]
        return text, token_counter.count_tokens(text)


class MockConflictDetector(IConflictDetector):
    def __init__(self) -> None:
        self.called = False

    async def detect(self, items, config):
        self.called = True
        _ = config
        if len(items) >= 2:
            return [
                ConflictGroup(
                    entity_tag="x",
                    attribute="x:numeric",
                    item_ids=[items[0].item_id, items[1].item_id],
                )
            ]
        return []


class MockStitcher(IContextStitcher):
    def __init__(self) -> None:
        self.called = False

    async def stitch(self, items, token_counter):
        self.called = True
        return [
            ContextBlock(
                item_id=item.item_id,
                document_id=item.doc_id,
                text=text,
                token_count=token_counter.count_tokens(text),
                compressed=compressed,
            )
            for item, text, compressed in items
        ]


def _pipeline(
    budget: int = 6300,
    *,
    conflict: IConflictDetector | None = None,
    stitcher: IContextStitcher | None = None,
) -> ContextBuilderPipeline:
    counter = CharacterApproximationTokenCounter()
    return ContextBuilderPipeline(
        budget_allocator=MockBudgetAllocator(budget),
        compressor=MockCompressor(),
        conflict_detector=conflict or MockConflictDetector(),
        stitcher=stitcher or MockStitcher(),
        token_counter=counter,
    )


@pytest.mark.asyncio
async def test_us1_over_budget_pack_within_budget(default_config):
    pack = build_synthetic_pack(n_items=20, tokens_per_item=600)
    pipeline = ContextBuilderRegistry.build(default_config)
    ctx = await pipeline.build(pack, default_config)
    assert ctx.token_count <= default_config.available_budget
    assert len(ctx.ordered_blocks) == len(ctx.citation_map)
    assert len(ctx.ordered_blocks) < 20


@pytest.mark.asyncio
async def test_full_pipeline_stage_ordering():
    conflict = MockConflictDetector()
    stitcher = MockStitcher()
    pipeline = _pipeline(conflict=conflict, stitcher=stitcher)
    pack = make_pack([make_item(), make_item(chunk_id="c2", relevance_score=0.5)])
    config = ContextBuilderConfig()
    await pipeline.build(pack, config)
    assert conflict.called
    assert stitcher.called


@pytest.mark.asyncio
async def test_evidence_pack_version_error_on_major_mismatch():
    pack = build_synthetic_pack(n_items=2, tokens_per_item=10)
    pack = pack.model_copy(update={"schema_version": "2.0.0"})
    pipeline = _pipeline()
    config = ContextBuilderConfig(evidence_pack_schema_version="1.0.0")
    with pytest.raises(EvidencePackVersionError):
        await pipeline.build(pack, config)


@pytest.mark.asyncio
async def test_empty_budget_error():
    pack = make_pack([make_item()])
    pipeline = _pipeline(budget=0)
    config = ContextBuilderConfig()
    with pytest.raises(EmptyBudgetError):
        await pipeline.build(pack, config)


@pytest.mark.asyncio
async def test_timeout_returns_partial_context(monkeypatch):
    pack = make_pack([make_item()])
    pipeline = _pipeline()

    async def slow_inner(*_args, **_kwargs):
        await asyncio.sleep(0.05)
        raise AssertionError("should timeout before completion")

    monkeypatch.setattr(pipeline, "_build_inner", slow_inner)
    config = ContextBuilderConfig(timeout_seconds=0.01)
    ctx = await pipeline.build(pack, config)
    assert ctx.metadata.timeout is True
    assert ctx.ordered_blocks == []


def test_citation_integrity_validator_fires():
    block = ContextBlock(
        item_id="ei_test",
        document_id="doc1",
        text="hello",
        token_count=2,
    )
    with pytest.raises(CitationIntegrityError):
        _assert_citation_integrity([block], {})


def test_registry_unknown_compression_strategy_raises():
    config = ContextBuilderConfig(compression_strategy="unknown")
    with pytest.raises(ValueError, match="compression_strategy"):
        ContextBuilderRegistry.build(config)


def test_registry_unknown_token_counter_raises():
    config = ContextBuilderConfig(token_counter="unknown")
    with pytest.raises(ValueError, match="token_counter"):
        ContextBuilderRegistry.build(config)


@pytest.mark.asyncio
@pytest.mark.parametrize("bench", [True], ids=["bench"])
async def test_pipeline_bench_median_under_150ms(bench):
    pack = build_synthetic_pack(n_items=50, tokens_per_item=80)
    pipeline = ContextBuilderRegistry.build(ContextBuilderConfig())
    config = ContextBuilderConfig(
        total_context_window=8000,
        reservations=BudgetReservations(system_prompt=500, question=200, output=1000),
    )

    timings: list[float] = []
    for _ in range(5):
        start = time.perf_counter()
        await pipeline.build(pack, config)
        timings.append((time.perf_counter() - start) * 1000.0)

    assert statistics.median(timings) <= 150.0
