"""Unit tests for PackAssembler."""

from __future__ import annotations

import pytest

from core.evidence_orchestrator.collection.retrieval_result_collector import (
    RetrievalResultCollector,
)
from core.evidence_orchestrator.deduplication.embedding_deduplicator import (
    EmbeddingDeduplicator,
)
from core.evidence_orchestrator.models import OrchestratorTrace
from core.evidence_orchestrator.packaging.pack_assembler import PackAssembler
from tests.unit.core.evidence_orchestrator.conftest import make_candidate, make_result


async def _assemble_duplicates(count: int, plan, config):
    text = "duplicate token content for ratio test"
    candidates = [
        make_candidate(chunk_id=f"c{i}", content_excerpt=text, rank=i + 1)
        for i in range(count)
    ]
    result = make_result(candidates)
    collected = await RetrievalResultCollector().collect(result, plan, config)
    deduped = await EmbeddingDeduplicator().deduplicate(collected, config)
    assembler = PackAssembler()
    items = assembler.collected_to_evidence_items(deduped)
    return assembler.assemble(
        items=items,
        result=result,
        plan=plan,
        trace=OrchestratorTrace(),
        raw_input_token_count=sum(
            assembler._token_counter.count_tokens(c.content_excerpt)  # noqa: SLF001
            for c in candidates
        ),
    )


@pytest.mark.asyncio
async def test_token_reduction_ratio(minimal_retrieval_plan, default_config):
    pack = await _assemble_duplicates(10, minimal_retrieval_plan, default_config)
    assert pack.token_reduction_ratio is not None
    assert pack.token_reduction_ratio <= 0.85
    assert pack.token_reduction_ratio > 0.0


@pytest.mark.asyncio
async def test_citation_and_sources(minimal_retrieval_plan, default_config):
    candidate = make_candidate()
    result = make_result([candidate])
    collected = await RetrievalResultCollector().collect(
        result, minimal_retrieval_plan, default_config
    )
    assembler = PackAssembler()
    items = assembler.collected_to_evidence_items(collected)
    pack = assembler.assemble(
        items=items,
        result=result,
        plan=minimal_retrieval_plan,
        trace=OrchestratorTrace(),
        raw_input_token_count=10,
    )
    item = pack.items[0]
    assert item.citation.document_id == "doc1"
    assert item.citation.chunk_id == candidate.chunk_id
    assert len(item.sources) >= 1


@pytest.mark.asyncio
async def test_schema_version(minimal_retrieval_plan, default_config):
    pack = await _assemble_duplicates(2, minimal_retrieval_plan, default_config)
    assert pack.schema_version == "1.0.0"
