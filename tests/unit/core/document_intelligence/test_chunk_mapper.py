"""Unit tests for map_elements_to_chunks invariants (FR-005/FR-006)."""

from __future__ import annotations

from core.document_intelligence.chunk_mapper import map_elements_to_chunks
from core.document_intelligence.model import StructuralElement
from fields.schemas import ElementChunkConfig


def _para(i: int, text: str) -> StructuralElement:
    return StructuralElement(
        id=f"doc:para:{i}",
        type="paragraph",
        order=i,
        text=text,
        provenance={},
    )


def _row(i: int, name: str) -> StructuralElement:
    return StructuralElement(
        id=f"doc:row:{i}",
        type="table-row",
        order=i,
        fields={"Name": name},
        provenance={"row_index": i + 2, "sheet_name": "Sheet1"},
    )


def test_no_split_table_rows():
    elements = [_row(0, "a"), _row(1, "b"), _row(2, "c")]
    config = {"table-row": ElementChunkConfig(group=False)}
    chunks = map_elements_to_chunks(elements, config)
    assert len(chunks) == 3
    for chunk, el in zip(chunks, elements):
        assert chunk["metadata"]["source_element_ids"] == [el.id]
        assert chunk["metadata"]["element_type"] == "table-row"


def test_grouping_adjacent_paragraphs():
    elements = [_para(0, "aa"), _para(1, "bb"), _para(2, "cc")]
    config = {"paragraph": ElementChunkConfig(group=True, max_chunk_chars=20)}
    chunks = map_elements_to_chunks(elements, config, default_max_chars=20)
    assert len(chunks) == 1
    assert chunks[0]["metadata"]["source_element_ids"] == [e.id for e in elements]


def test_order_preserved():
    elements = [_row(0, "a"), _para(1, "p"), _row(2, "b")]
    config = {
        "table-row": ElementChunkConfig(group=False),
        "paragraph": ElementChunkConfig(group=False),
    }
    chunks = map_elements_to_chunks(elements, config)
    assert [c["metadata"]["element_type"] for c in chunks] == [
        "table-row",
        "paragraph",
        "table-row",
    ]


def test_oversized_element_split_exception():
    big = _para(0, "x" * 50)
    config = {"paragraph": ElementChunkConfig(group=False, max_chunk_chars=20)}
    chunks = map_elements_to_chunks(big and [big], config, default_max_chars=20, overlap=0)
    assert len(chunks) > 1
    assert all(c["metadata"]["source_element_ids"] == [big.id] for c in chunks)
