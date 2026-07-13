"""DocumentModel + StructuralElement (FR-001a / FR-003a)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

StructuralElementType = Literal[
    "section",
    "paragraph",
    "table",
    "table-row",
    "list",
    "list-item",
]

CANONICAL_ELEMENT_TYPES: frozenset[str] = frozenset(
    {"section", "paragraph", "table", "table-row", "list", "list-item"}
)

ExtractionOutcome = Literal["full", "degraded"]
DegradationReason = Literal["unsupported_structure", "parse_error", "empty_content"]


def make_element_id(asset_fingerprint: str, element_path: str) -> str:
    """Deterministic stable id: ``{asset_fingerprint}:{element_path}`` (research R3)."""
    fingerprint = (asset_fingerprint or "").strip() or "unknown"
    path = (element_path or "").strip() or "0"
    return f"{fingerprint}:{path}"


class StructuralElement(BaseModel):
    """One unit within a parsed DocumentModel."""

    model_config = ConfigDict(extra="forbid")

    id: str
    type: StructuralElementType
    order: int
    text: str | None = None
    fields: dict[str, str] | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    parent_id: str | None = None

    @model_validator(mode="after")
    def _require_text_or_fields(self) -> "StructuralElement":
        has_text = self.text is not None
        has_fields = self.fields is not None
        if self.type == "table-row":
            if not has_fields:
                raise ValueError("table-row elements require fields")
            if has_text:
                raise ValueError("table-row elements must not set text")
        else:
            if not has_text:
                raise ValueError(f"{self.type} elements require text")
            if has_fields:
                raise ValueError(f"{self.type} elements must not set fields")
        return self


class DocumentModel(BaseModel):
    """Root container for one parsed source document."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int | str
    source_format: str
    elements: list[StructuralElement] = Field(default_factory=list)
    extraction_outcome: ExtractionOutcome = "full"
    degradation_reason: DegradationReason | None = None

    @model_validator(mode="after")
    def _degradation_consistency(self) -> "DocumentModel":
        if self.extraction_outcome == "degraded":
            if self.degradation_reason is None:
                raise ValueError("degraded models require degradation_reason")
        elif self.degradation_reason is not None:
            raise ValueError("degradation_reason only allowed when outcome is degraded")

        ids = [el.id for el in self.elements]
        if len(ids) != len(set(ids)):
            raise ValueError("StructuralElement.id must be unique within a DocumentModel")
        return self

    def element_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for el in self.elements:
            counts[el.type] = counts.get(el.type, 0) + 1
        return counts
