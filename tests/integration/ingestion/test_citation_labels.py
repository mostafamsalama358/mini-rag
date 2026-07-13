"""Integration: citation labels differ by pack template (US5)."""

from __future__ import annotations

from services.FieldRegistry import FieldRegistry
from utils.chunk_metadata import format_source_label


def test_pharmacy_vs_legal_citation_templates():
    registry = FieldRegistry().load()
    pharmacy = registry.build_profile("pharmacy")
    legal = registry.build_profile("legal")

    meta = {
        "file_name": "doc.xlsx",
        "row_index": 5,
        "sheet_name": "Sheet1",
        "article_number": "12",
        "page": 3,
    }
    ph_label = format_source_label(
        meta,
        label_template=pharmacy.metadata.label_template,
    )
    legal_label = format_source_label(
        meta,
        label_template=legal.metadata.label_template,
    )
    assert ph_label != legal_label
    assert "row" in ph_label.lower() or "5" in ph_label
    assert "12" in legal_label or "مادة" in legal_label
