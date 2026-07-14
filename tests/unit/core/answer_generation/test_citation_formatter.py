"""Unit tests for ItemIdCitationFormatter."""

from __future__ import annotations

from core.answer_generation.citation.item_id_formatter import ItemIdCitationFormatter
from tests.unit.core.answer_generation.conftest import _citation


def test_resolved_citations_in_first_appearance_order() -> None:
    citation_map = {
        "ei_aaaa000000000001": _citation(document_id="doc_a", chunk_id="c1"),
        "ei_bbbb000000000002": _citation(document_id="doc_b", chunk_id="c2"),
    }
    answer = (
        "Second [ei_bbbb000000000002] then first [ei_aaaa000000000001] "
        "and second again [ei_bbbb000000000002]."
    )
    citations = ItemIdCitationFormatter().format(answer, citation_map)

    assert [c.citation_id for c in citations] == [
        "ei_bbbb000000000002",
        "ei_aaaa000000000001",
    ]


def test_unknown_markers_omitted() -> None:
    answer = "Unknown marker [ei_cccc000000000003]."
    citations = ItemIdCitationFormatter().format(answer, {})
    assert citations == []


def test_empty_answer_returns_empty_list() -> None:
    assert ItemIdCitationFormatter().format("", {"x": _citation()}) == []
