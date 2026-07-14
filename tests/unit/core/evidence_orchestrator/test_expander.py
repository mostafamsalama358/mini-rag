"""Unit tests for LineageExpander."""

from __future__ import annotations

import pytest

from core.chunking.models import Chunk, ChunkIdentity, ChunkRelationships
from core.evidence_orchestrator.collection.retrieval_result_collector import (
    RetrievalResultCollector,
)
from core.evidence_orchestrator.config import EvidenceOrchestratorConfig
from core.evidence_orchestrator.expansion.lineage_expander import LineageExpander
from tests.unit.core.evidence_orchestrator.conftest import (
    MockChunkReader,
    make_candidate,
    make_result,
)


def _chunk(chunk_id: str, **relationships) -> Chunk:
    return Chunk(
        text=f"TEXT_{chunk_id}",
        identity=ChunkIdentity(
            chunk_id=chunk_id,
            document_id="doc1",
            strategy_id="semantic",
            source_element_ids=[chunk_id],
        ),
        relationships=ChunkRelationships(**relationships),
    )


@pytest.mark.asyncio
async def test_expansion_high_score(minimal_retrieval_plan, default_config):
    prev_id = "prev1"
    candidate = make_candidate(chunk_id="main", score=0.90)
    result = make_result([candidate])
    collected = await RetrievalResultCollector().collect(
        result, minimal_retrieval_plan, default_config
    )
    reader = MockChunkReader(
        {
            ("main", "doc1"): _chunk("main", previous_chunk_id=prev_id),
            (prev_id, "doc1"): _chunk(prev_id),
        }
    )
    expanded = await LineageExpander().expand(
        collected, reader, default_config
    )
    assert expanded[0].expanded is True
    assert expanded[0].effective_text.startswith("TEXT_prev1")


@pytest.mark.asyncio
async def test_expansion_disabled(minimal_retrieval_plan):
    config = EvidenceOrchestratorConfig(expansion_enabled=False)
    candidate = make_candidate(chunk_id="main", score=0.90)
    result = make_result([candidate])
    collected = await RetrievalResultCollector().collect(
        result, minimal_retrieval_plan, config
    )
    reader = MockChunkReader(
        {("main", "doc1"): _chunk("main", next_chunk_id="next1")}
    )
    expanded = await LineageExpander().expand(collected, reader, config)
    assert reader.calls == []
    assert expanded[0].expanded is False


@pytest.mark.asyncio
async def test_low_score_skipped(minimal_retrieval_plan, default_config):
    candidate = make_candidate(chunk_id="main", score=0.50)
    result = make_result([candidate])
    collected = await RetrievalResultCollector().collect(
        result, minimal_retrieval_plan, default_config
    )
    reader = MockChunkReader(
        {("main", "doc1"): _chunk("main", next_chunk_id="next1")}
    )
    expanded = await LineageExpander().expand(
        collected, reader, default_config
    )
    assert expanded[0].expanded is False


@pytest.mark.asyncio
async def test_chunk_not_found_keeps_original(
    minimal_retrieval_plan, default_config
):
    candidate = make_candidate(chunk_id="missing", score=0.90)
    result = make_result([candidate])
    collected = await RetrievalResultCollector().collect(
        result, minimal_retrieval_plan, default_config
    )
    reader = MockChunkReader()
    expanded = await LineageExpander().expand(
        collected, reader, default_config
    )
    assert expanded[0].expanded is False
    assert expanded[0].effective_text == candidate.content_excerpt


@pytest.mark.asyncio
async def test_fetch_exception_keeps_original(
    minimal_retrieval_plan, default_config
):
    candidate = make_candidate(chunk_id="main", score=0.90)
    result = make_result([candidate])
    collected = await RetrievalResultCollector().collect(
        result, minimal_retrieval_plan, default_config
    )

    class FailingReader(MockChunkReader):
        async def get_chunk(self, chunk_id: str, document_id: str):
            if chunk_id == "main":
                return _chunk("main", next_chunk_id="next1")
            raise RuntimeError("fetch failed")

    expanded = await LineageExpander().expand(
        collected, FailingReader(), default_config
    )
    assert expanded[0].expanded is False
