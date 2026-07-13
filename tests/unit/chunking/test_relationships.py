"""US3: hierarchical relationship-aware chunk output."""

from __future__ import annotations

import core.chunking.strategies  # noqa: F401
from core.chunking.models import ChunkingStrategyConfig
from core.chunking.registry import get_chunking_strategy
from tests.fixtures.chunking.heading_table_sections import FIXTURE_DOC


def _chunk_set():
    config = ChunkingStrategyConfig(max_chars=800)
    strategy = get_chunking_strategy("semantic_structural", config)
    return strategy.chunk(FIXTURE_DOC, config)


def test_child_chunk_ids_resolve():
    chunk_set = _chunk_set()
    ids = {c.identity.chunk_id for c in chunk_set.chunks if c.identity}
    for chunk in chunk_set.chunks:
        for child_id in chunk.relationships.child_chunk_ids:
            assert child_id in ids


def test_next_chain_visits_every_chunk_once():
    chunk_set = _chunk_set()
    by_id = {c.identity.chunk_id: c for c in chunk_set.chunks if c.identity}
    start = next(c for c in chunk_set.chunks if c.structural_context and c.structural_context.position == 0)
    visited = []
    current = start
    while current is not None:
        visited.append(current.identity.chunk_id)
        next_id = current.relationships.next_chunk_id
        current = by_id.get(next_id) if next_id else None
    assert len(visited) == len(chunk_set.chunks)
    assert len(set(visited)) == len(visited)


def test_no_dangling_relationship_references():
    chunk_set = _chunk_set()
    ids = {c.identity.chunk_id for c in chunk_set.chunks if c.identity}
    for chunk in chunk_set.chunks:
        rel = chunk.relationships
        for ref in (rel.parent_chunk_id, rel.previous_chunk_id, rel.next_chunk_id):
            if ref is not None:
                assert ref in ids
        for child_id in rel.child_chunk_ids:
            assert child_id in ids


def test_section_level_chunk_has_children():
    chunk_set = _chunk_set()
    heading_chunks = [
        c for c in chunk_set.chunks if c.structural_context and c.structural_context.element_type == "heading"
    ]
    assert any(c.relationships.child_chunk_ids for c in heading_chunks)
