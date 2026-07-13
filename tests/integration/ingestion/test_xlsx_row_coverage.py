"""Integration: SC-001 — 50-row xlsx → 50 unsplit table-row chunks."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.document_intelligence.chunk_mapper import map_elements_to_chunks
from core.document_intelligence.parsers.xlsx_parser import XlsxDocumentParser
from fields.schemas import ElementChunkConfig

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "document_intelligence"


@pytest.fixture(scope="module", autouse=True)
def _ensure_fixtures():
    if not (FIXTURES / "sample_50_rows.xlsx").exists():
        from tests.fixtures.document_intelligence.generate_fixtures import generate

        generate()


def test_xlsx_row_coverage_sc001():
    path = FIXTURES / "sample_50_rows.xlsx"
    model = XlsxDocumentParser().parse(str(path), "sample_50_rows.xlsx")
    assert len([e for e in model.elements if e.type == "table-row"]) == 50

    chunks = map_elements_to_chunks(
        model.elements,
        {"table-row": ElementChunkConfig(group=False, metadata_keys=["row_index"])},
        file_name="sample_50_rows.xlsx",
    )
    assert len(chunks) == 50
    row_indices = [c["metadata"]["row_index"] for c in chunks]
    assert len(set(row_indices)) == 50
    assert all(len(c["metadata"]["source_element_ids"]) == 1 for c in chunks)
    assert all(c["metadata"]["element_type"] == "table-row" for c in chunks)
