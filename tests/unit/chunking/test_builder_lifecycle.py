"""US6/SC-012: ChunkBuilder lifecycle integrity."""

from __future__ import annotations

import core.chunking.strategies  # noqa: F401
from core.chunking.builder import ChunkBuilder
from core.chunking.models import BoundaryDecision, ChunkingStrategyConfig
from core.document_intelligence.model import DocumentModel, StructuralElement
from tests.fixtures.chunking.heading_table_sections import FIXTURE_DOC


def test_identity_assigned_on_close_not_before():
    builder = ChunkBuilder(
        FIXTURE_DOC,
        ChunkingStrategyConfig(max_chars=800),
        "semantic_structural",
    )
    element = FIXTURE_DOC.elements[0]
    builder.open_chunk(element)
    assert builder._open_elements
    assert not builder.chunks

    decision = BoundaryDecision(
        decision="split",
        applied_rule="test",
        triggered_features=["size_budget"],
        rationale="close",
    )
    builder.close_chunk(decision)
    assert builder.chunks
    assert builder.chunks[0].identity is not None
    assert builder._identity_assigned_after_close


def test_validation_report_status_values():
    from core.chunking.validator import ChunkValidator

    report = ChunkValidator().validate([])
    assert report.status in ("pass", "fail", "pass_with_warnings")
