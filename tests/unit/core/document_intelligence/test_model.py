"""Unit tests for DocumentModel / StructuralElement (FR-001a / FR-003a)."""

from __future__ import annotations

import pytest

from core.document_intelligence.model import (
    CANONICAL_ELEMENT_TYPES,
    DocumentModel,
    StructuralElement,
    make_element_id,
)


def test_canonical_vocabulary():
    assert CANONICAL_ELEMENT_TYPES == {
        "section",
        "paragraph",
        "table",
        "table-row",
        "list",
        "list-item",
    }


def test_stable_id_determinism():
    a = make_element_id("fp1", "sheet:0/row:2")
    b = make_element_id("fp1", "sheet:0/row:2")
    assert a == b == "fp1:sheet:0/row:2"


def test_table_row_requires_fields():
    with pytest.raises(ValueError):
        StructuralElement(
            id="x:1",
            type="table-row",
            order=0,
            text="nope",
            provenance={},
        )


def test_paragraph_requires_text():
    with pytest.raises(ValueError):
        StructuralElement(
            id="x:1",
            type="paragraph",
            order=0,
            fields={"a": "b"},
            provenance={},
        )


def test_document_model_rejects_duplicate_ids():
    el = StructuralElement(
        id="same",
        type="paragraph",
        order=0,
        text="hi",
        provenance={},
    )
    el2 = StructuralElement(
        id="same",
        type="paragraph",
        order=1,
        text="bye",
        provenance={},
    )
    with pytest.raises(ValueError):
        DocumentModel(asset_id=1, source_format="txt", elements=[el, el2])


def test_degraded_requires_reason():
    with pytest.raises(ValueError):
        DocumentModel(
            asset_id=1,
            source_format="txt",
            elements=[],
            extraction_outcome="degraded",
        )
