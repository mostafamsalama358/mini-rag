"""Unit tests for RetrievalResultCollector."""

from __future__ import annotations

import pytest

from core.evidence_orchestrator.collection.retrieval_result_collector import (
    RetrievalResultCollector,
)
from tests.unit.core.evidence_orchestrator.conftest import make_candidate, make_result


@pytest.mark.asyncio
async def test_single_candidate(minimal_retrieval_plan, default_config):
    result = make_result([make_candidate()])
    collector = RetrievalResultCollector()
    items = await collector.collect(result, minimal_retrieval_plan, default_config)
    assert len(items) == 1
    assert items[0].strategy_id == "semantic"
    assert items[0].raw_token_count > 0


@pytest.mark.asyncio
async def test_empty_candidates(minimal_retrieval_plan, default_config):
    result = make_result([])
    collector = RetrievalResultCollector()
    items = await collector.collect(result, minimal_retrieval_plan, default_config)
    assert items == []


@pytest.mark.asyncio
async def test_strategy_id_from_trace(minimal_retrieval_plan, default_config):
    c1 = make_candidate(chunk_id="c1", strategy_index=0)
    c2 = make_candidate(chunk_id="c2", strategy_index=1, rank=2)
    result = make_result([c1, c2], strategies=("semantic", "keyword"))
    collector = RetrievalResultCollector()
    items = await collector.collect(result, minimal_retrieval_plan, default_config)
    assert items[0].strategy_id == "semantic"
    assert items[1].strategy_id == "keyword"


@pytest.mark.asyncio
async def test_source_ref_none_handled(minimal_retrieval_plan, default_config):
    candidate = make_candidate(source_ref=None)
    result = make_result([candidate])
    collector = RetrievalResultCollector()
    items = await collector.collect(result, minimal_retrieval_plan, default_config)
    assert len(items) == 1


@pytest.mark.asyncio
async def test_raw_token_count_character_approximation(
    minimal_retrieval_plan, default_config
):
    text = "a" * 40
    candidate = make_candidate(content_excerpt=text)
    result = make_result([candidate])
    collector = RetrievalResultCollector()
    items = await collector.collect(result, minimal_retrieval_plan, default_config)
    assert items[0].raw_token_count == 10
