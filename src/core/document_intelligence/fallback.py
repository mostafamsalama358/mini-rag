"""Degraded single-section DocumentModel construction (FR-011)."""

from __future__ import annotations

from core.document_intelligence.errors import DegradationReason
from core.document_intelligence.model import (
    DocumentModel,
    StructuralElement,
    make_element_id,
)


def build_fallback_model(
    asset_id: int | str,
    source_format: str,
    best_effort_text: str | None,
    reason: DegradationReason,
    *,
    asset_fingerprint: str | None = None,
) -> DocumentModel:
    """Build a minimal degraded DocumentModel (whole text as one section)."""
    fingerprint = asset_fingerprint or str(asset_id)
    elements: list[StructuralElement] = []
    text = (best_effort_text or "").strip()
    if text:
        elements.append(
            StructuralElement(
                id=make_element_id(fingerprint, "section:0"),
                type="section",
                order=0,
                text=text,
                provenance={"fallback": True},
            )
        )
    return DocumentModel(
        asset_id=asset_id,
        source_format=source_format.lstrip("."),
        elements=elements,
        extraction_outcome="degraded",
        degradation_reason=reason,
    )
