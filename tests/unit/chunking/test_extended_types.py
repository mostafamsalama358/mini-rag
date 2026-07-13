"""US5: extended structural types are atomic semantic units."""

from __future__ import annotations

import core.chunking.strategies  # noqa: F401
from core.chunking.models import ChunkingStrategyConfig
from core.chunking.registry import get_chunking_strategy
from tests.fixtures.chunking.extended_types import EXTENDED_DOC


def _chunk_set():
    config = ChunkingStrategyConfig(max_chars=800)
    strategy = get_chunking_strategy("semantic_structural", config)
    return strategy.chunk(EXTENDED_DOC, config)


def _ids(chunk) -> set[str]:
    return set(chunk.metadata.get("source_element_ids") or [])


def test_code_block_not_merged_with_paragraphs():
    chunk_set = _chunk_set()
    for chunk in chunk_set.chunks:
        ids = _ids(chunk)
        if "test-002:cb1" in ids:
            assert "test-002:p1" not in ids
            assert "test-002:p2" not in ids


def test_figure_placeholder_has_own_chunk():
    chunk_set = _chunk_set()
    fig_chunks = [c for c in chunk_set.chunks if "test-002:fig1" in _ids(c)]
    assert len(fig_chunks) == 1
    assert fig_chunks[0].text.strip()


def test_quote_not_merged_with_non_quote():
    chunk_set = _chunk_set()
    quote_chunks = [c for c in chunk_set.chunks if "test-002:q1" in _ids(c)]
    assert len(quote_chunks) == 1
    assert _ids(quote_chunks[0]) == {"test-002:q1"}


def test_atomic_types_have_chunk_id():
    chunk_set = _chunk_set()
    for element_id in ("test-002:cb1", "test-002:q1", "test-002:fig1"):
        matching = [c for c in chunk_set.chunks if element_id in _ids(c)]
        assert matching
        assert matching[0].identity and matching[0].identity.chunk_id
