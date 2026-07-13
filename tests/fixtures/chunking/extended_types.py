"""Scenario 5 fixture: paragraph → code-block → paragraph → quote → figure."""

from __future__ import annotations

from core.document_intelligence.model import DocumentModel, StructuralElement

EXTENDED_DOC = DocumentModel(
    asset_id="test-002",
    source_format="txt",
    elements=[
        StructuralElement(id="test-002:p1", type="paragraph", order=0, text="Before code."),
        StructuralElement(
            id="test-002:cb1",
            type="code-block",
            order=1,
            text="def foo():\n    return 42",
        ),
        StructuralElement(id="test-002:p2", type="paragraph", order=2, text="After code."),
        StructuralElement(
            id="test-002:q1",
            type="quote",
            order=3,
            text="The only way to do great work is to love what you do.",
        ),
        StructuralElement(
            id="test-002:fig1",
            type="figure-placeholder",
            order=4,
            text="[Figure 1: Architecture diagram]",
        ),
    ],
)
