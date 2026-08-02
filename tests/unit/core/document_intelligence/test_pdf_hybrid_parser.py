"""Unit tests for hybrid PDF parser routing (OpenDataLoader + OCR)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core.document_intelligence.parsers.pdf_parser import PdfDocumentParser
from utils.opendataloader_pdf import json_to_structural_elements
from utils.pdf_page_detect import PageSearchability, searchable_ratio

FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "document_intelligence"


@pytest.fixture(scope="module", autouse=True)
def _ensure_fixtures():
    if not (FIXTURES / "sample_with_table.pdf").exists():
        from tests.fixtures.document_intelligence.generate_fixtures import generate

        generate()


def test_searchable_ratio():
    pages = [
        PageSearchability(1, True, 100),
        PageSearchability(2, False, 0),
        PageSearchability(3, True, 40),
    ]
    assert searchable_ratio(pages) == pytest.approx(2 / 3)
    assert searchable_ratio([]) == 0.0


def test_odl_json_maps_heading_paragraph_table():
    odl_doc = {
        "file name": "demo.pdf",
        "number of pages": 1,
        "kids": [
            {
                "type": "heading",
                "id": 1,
                "page number": 1,
                "heading level": 1,
                "content": "Controls",
            },
            {
                "type": "paragraph",
                "id": 2,
                "page number": 1,
                "content": "COSO framework overview.",
            },
            {
                "type": "table",
                "id": 3,
                "page number": 1,
                "number of rows": 1,
                "number of columns": 2,
                "rows": [
                    {
                        "type": "table row",
                        "row number": 1,
                        "cells": [
                            {
                                "row number": 1,
                                "column number": 1,
                                "kids": [{"type": "paragraph", "content": "A"}],
                            },
                            {
                                "row number": 1,
                                "column number": 2,
                                "kids": [{"type": "paragraph", "content": "B"}],
                            },
                        ],
                    }
                ],
            },
            {
                "type": "header",
                "page number": 1,
                "kids": [{"type": "paragraph", "content": "skip me"}],
            },
        ],
    }
    elements = json_to_structural_elements(odl_doc, file_id="demo.pdf")
    types = [el.type for el in elements]
    assert "heading" in types
    assert "paragraph" in types
    assert "table" in types
    assert "table-row" in types
    assert all(el.provenance.get("parser") == "opendataloader" for el in elements)
    assert not any("skip me" in (el.text or "") for el in elements)
    row = next(el for el in elements if el.type == "table-row")
    assert row.fields == {"col_1": "A", "col_2": "B"}


def test_hybrid_uses_odl_when_searchable(monkeypatch):
    monkeypatch.setenv("PDF_PARSER_MODE", "hybrid")
    from helpers.config import get_settings

    get_settings.cache_clear()

    sample = FIXTURES / "sample_with_table.pdf"
    fake_odl = {
        "file name": "sample_with_table.pdf",
        "number of pages": 1,
        "kids": [
            {
                "type": "paragraph",
                "id": 1,
                "page number": 1,
                "content": "OpenDataLoader extracted body",
            }
        ],
    }

    with (
        patch(
            "utils.opendataloader_pdf.is_opendataloader_available",
            return_value=True,
        ),
        patch(
            "utils.opendataloader_pdf.convert_pdf_to_json",
            return_value=fake_odl,
        ),
        patch(
            "utils.pdf_page_detect.classify_pdf_pages",
            return_value=[PageSearchability(1, True, 80)],
        ),
        patch("utils.pdf_ocr.extract_pages_with_ocr", return_value=[]) as ocr_mock,
    ):
        model = PdfDocumentParser().parse(str(sample), "sample_with_table.pdf")

    assert model.extraction_outcome == "full"
    assert any("OpenDataLoader extracted body" in (el.text or "") for el in model.elements)
    ocr_mock.assert_not_called()
    get_settings.cache_clear()


def test_hybrid_ocrs_non_searchable_pages(monkeypatch):
    monkeypatch.setenv("PDF_PARSER_MODE", "hybrid")
    from helpers.config import get_settings

    get_settings.cache_clear()

    sample = FIXTURES / "sample_with_table.pdf"
    fake_odl = {
        "file name": "sample_with_table.pdf",
        "number of pages": 2,
        "kids": [
            {
                "type": "paragraph",
                "id": 1,
                "page number": 1,
                "content": "Digital page from ODL",
            }
        ],
    }
    ocr_page = SimpleNamespace(
        page_content="Scanned page from OCR",
        metadata={"page": 2, "ocr_used": True, "parser": "ocr"},
    )

    with (
        patch(
            "utils.opendataloader_pdf.is_opendataloader_available",
            return_value=True,
        ),
        patch(
            "utils.opendataloader_pdf.convert_pdf_to_json",
            return_value=fake_odl,
        ),
        patch(
            "utils.pdf_page_detect.classify_pdf_pages",
            return_value=[
                PageSearchability(1, True, 80),
                PageSearchability(2, False, 0),
            ],
        ),
        patch("utils.pdf_ocr.extract_pages_with_ocr", return_value=[ocr_page]) as ocr_mock,
    ):
        model = PdfDocumentParser().parse(str(sample), "sample_with_table.pdf")

    texts = " ".join(el.text or "" for el in model.elements)
    assert "Digital page from ODL" in texts
    assert "Scanned page from OCR" in texts
    ocr_mock.assert_called_once()
    called_pages = set(ocr_mock.call_args.args[1])
    assert 2 in called_pages
    get_settings.cache_clear()


def test_legacy_mode_skips_odl(monkeypatch):
    monkeypatch.setenv("PDF_PARSER_MODE", "legacy")
    from helpers.config import get_settings

    get_settings.cache_clear()

    sample = FIXTURES / "sample_with_table.pdf"
    with (
        patch("utils.opendataloader_pdf.convert_pdf_to_json") as odl_mock,
        patch(
            "utils.pdf_ocr.load_pdf_with_ocr_fallback",
            return_value=[
                SimpleNamespace(
                    page_content="legacy text",
                    metadata={"page": 1, "ocr_used": False},
                )
            ],
        ),
    ):
        model = PdfDocumentParser().parse(str(sample), "sample_with_table.pdf")

    odl_mock.assert_not_called()
    assert model.elements[0].text == "legacy text"
    get_settings.cache_clear()


def test_falls_back_when_odl_unavailable(monkeypatch):
    monkeypatch.setenv("PDF_PARSER_MODE", "hybrid")
    from helpers.config import get_settings

    get_settings.cache_clear()

    sample = FIXTURES / "sample_with_table.pdf"
    with (
        patch(
            "utils.opendataloader_pdf.is_opendataloader_available",
            return_value=False,
        ),
        patch(
            "utils.pdf_page_detect.classify_pdf_pages",
            return_value=[PageSearchability(1, True, 80)],
        ),
        patch(
            "utils.pdf_ocr.load_pdf_with_ocr_fallback",
            return_value=[
                SimpleNamespace(
                    page_content="fallback text",
                    metadata={"page": 1, "ocr_used": False},
                )
            ],
        ) as legacy_mock,
    ):
        model = PdfDocumentParser().parse(str(sample), "sample_with_table.pdf")

    legacy_mock.assert_called_once()
    assert model.elements[0].text == "fallback text"
    get_settings.cache_clear()
