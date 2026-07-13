"""Unit tests for degraded fallback builder (FR-011)."""

from __future__ import annotations

from core.document_intelligence.fallback import build_fallback_model


def test_fallback_with_text():
    model = build_fallback_model(
        asset_id="f1",
        source_format="xlsx",
        best_effort_text="whole doc",
        reason="parse_error",
    )
    assert model.extraction_outcome == "degraded"
    assert model.degradation_reason == "parse_error"
    assert len(model.elements) == 1
    assert model.elements[0].type == "section"
    assert model.elements[0].text == "whole doc"


def test_fallback_empty_text():
    model = build_fallback_model(
        asset_id="f1",
        source_format="txt",
        best_effort_text="",
        reason="empty_content",
    )
    assert model.elements == []
    assert model.degradation_reason == "empty_content"
