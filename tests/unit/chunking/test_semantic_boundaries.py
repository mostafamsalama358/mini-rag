"""US1: semantic boundary decisions over token utilization."""

from __future__ import annotations

import core.chunking.strategies  # noqa: F401 — register default strategy
from core.chunking.models import ChunkingStrategyConfig
from core.chunking.registry import get_chunking_strategy
from tests.fixtures.chunking.heading_table_sections import FIXTURE_DOC


def _chunk_set():
    config = ChunkingStrategyConfig(max_chars=800)
    strategy = get_chunking_strategy("semantic_structural", config)
    return strategy.chunk(FIXTURE_DOC, config)


def _element_ids(chunk) -> set[str]:
    return set(chunk.metadata.get("source_element_ids") or [])


def test_heading_not_separated_from_first_paragraph():
    chunk_set = _chunk_set()
    merged = [
        chunk
        for chunk in chunk_set.chunks
        if {"test-001:h1", "test-001:p1"}.issubset(_element_ids(chunk))
    ]
    assert merged, "heading must stay with first paragraph"


def test_table_rows_not_merged_across_rows():
    chunk_set = _chunk_set()
    for chunk in chunk_set.chunks:
        ids = _element_ids(chunk)
        assert not ({"test-001:tr1", "test-001:tr2"}.issubset(ids))


def test_no_chunk_spans_both_headings():
    chunk_set = _chunk_set()
    for chunk in chunk_set.chunks:
        ids = _element_ids(chunk)
        assert not (
            any(eid in ids for eid in ("test-001:h1", "test-001:p1", "test-001:p2"))
            and any(eid in ids for eid in ("test-001:h2", "test-001:p3"))
        )


def test_heading_path_on_section_a_chunks():
    chunk_set = _chunk_set()
    section_a_chunks = [
        c
        for c in chunk_set.chunks
        if _element_ids(c)
        & {"test-001:p1", "test-001:p2", "test-001:tr1", "test-001:tr2"}
    ]
    assert section_a_chunks
    for chunk in section_a_chunks:
        assert "Section A" in (chunk.metadata.get("heading_path") or [])
