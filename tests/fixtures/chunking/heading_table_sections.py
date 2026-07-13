"""Scenario 1 fixture: heading → paragraphs → table rows → new heading → paragraph."""

from __future__ import annotations

from core.document_intelligence.model import DocumentModel, StructuralElement

FIXTURE_DOC = DocumentModel(
    asset_id="test-001",
    source_format="txt",
    elements=[
        StructuralElement(id="test-001:h1", type="heading", order=0, text="Section A"),
        StructuralElement(id="test-001:p1", type="paragraph", order=1, text="Paragraph one."),
        StructuralElement(id="test-001:p2", type="paragraph", order=2, text="Paragraph two."),
        StructuralElement(id="test-001:t1", type="table", order=3, text="Table header."),
        StructuralElement(
            id="test-001:tr1",
            type="table-row",
            order=4,
            fields={"col1": "A", "col2": "B"},
            parent_id="test-001:t1",
        ),
        StructuralElement(
            id="test-001:tr2",
            type="table-row",
            order=5,
            fields={"col1": "C", "col2": "D"},
            parent_id="test-001:t1",
        ),
        StructuralElement(id="test-001:h2", type="heading", order=6, text="Section B"),
        StructuralElement(id="test-001:p3", type="paragraph", order=7, text="Separate section."),
    ],
)
