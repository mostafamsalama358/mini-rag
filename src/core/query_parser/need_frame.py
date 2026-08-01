"""NeedFrame model for pharmacy recommend-mode (Feature 020)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Acuity = Literal["acute", "chronic", "unknown"]


class NeedFrame(BaseModel):
    """Optional structured therapeutic need — all fields optional per query."""

    model_config = ConfigDict(extra="forbid")

    normalized_need: str | None = None
    population: str | None = None
    severity: str | None = None
    duration: str | None = None
    acuity: Acuity | None = None
    multiple_symptoms: list[str] = Field(default_factory=list)
    existing_diagnosis: str | None = None
    goal: str | None = None
    language: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    raw_need_span: str | None = None
    indication_tags: list[str] = Field(default_factory=list)
    taxonomy_node_ids: list[str] = Field(default_factory=list)
    ambiguity_group: str | None = None
