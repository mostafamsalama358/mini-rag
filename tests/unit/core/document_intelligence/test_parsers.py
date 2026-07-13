"""Unit tests for format parsers."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.document_intelligence.errors import DocumentIntelligenceDegraded
from core.document_intelligence.parsers.csv_parser import CsvDocumentParser
from core.document_intelligence.parsers.text_parser import TextDocumentParser
from core.document_intelligence.parsers.xlsx_parser import XlsxDocumentParser

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "document_intelligence"


@pytest.fixture(scope="module", autouse=True)
def _ensure_fixtures():
    if not (FIXTURES / "sample_50_rows.xlsx").exists():
        from tests.fixtures.document_intelligence.generate_fixtures import generate

        generate()


def test_xlsx_parser_row_count():
    path = FIXTURES / "sample_50_rows.xlsx"
    model = XlsxDocumentParser().parse(str(path), "sample_50_rows.xlsx")
    assert model.extraction_outcome == "full"
    assert len(model.elements) == 50
    assert all(el.type == "table-row" for el in model.elements)
    assert model.elements[0].fields is not None
    assert "Drug" in model.elements[0].fields
    assert model.elements[0].provenance.get("row_index") == 2


def test_xlsx_stable_ids():
    path = FIXTURES / "sample_50_rows.xlsx"
    a = XlsxDocumentParser().parse(str(path), "sample_50_rows.xlsx")
    b = XlsxDocumentParser().parse(str(path), "sample_50_rows.xlsx")
    assert [e.id for e in a.elements] == [e.id for e in b.elements]


def test_csv_parser():
    path = FIXTURES / "sample.csv"
    model = CsvDocumentParser().parse(str(path), "sample.csv")
    assert len(model.elements) == 10
    assert all(el.type == "table-row" for el in model.elements)


def test_text_parser():
    path = FIXTURES / "sample.txt"
    model = TextDocumentParser().parse(str(path), "sample.txt")
    assert model.extraction_outcome == "full"
    assert len(model.elements) >= 1
    assert all(el.type == "paragraph" for el in model.elements)


def test_malformed_xlsx_degrades():
    path = FIXTURES / "malformed.xlsx"
    with pytest.raises(DocumentIntelligenceDegraded) as exc:
        XlsxDocumentParser().parse(str(path), "malformed.xlsx")
    assert exc.value.reason == "empty_content"
