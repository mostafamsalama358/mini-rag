"""Unit tests for format_source_label template wiring (FR-015)."""

from __future__ import annotations

from utils.chunk_metadata import format_source_label


def test_legacy_format_unchanged():
    label = format_source_label({"file_name": "doc.pdf", "page": 3}, lang="en")
    assert label == "doc.pdf — page 3"


def test_label_template():
    label = format_source_label(
        {"file_name": "drugs.xlsx", "row_index": 12, "sheet_name": "Sheet1"},
        label_template="{file_name} — row {row_index}",
    )
    assert label == "drugs.xlsx — row 12"


def test_missing_template_key_becomes_empty():
    label = format_source_label(
        {"file_name": "a.pdf"},
        label_template="{file_name} — مادة {article_number}",
    )
    assert "a.pdf" in label
