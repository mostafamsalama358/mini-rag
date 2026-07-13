"""Pydantic models for the Intelligent Chunking Engine (spec 007)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fields.schemas import ElementChunkConfig

SizeBudgetStatus = Literal["within_limit", "over_limit"]
ValidationStatus = Literal["pass", "fail", "pass_with_warnings"]


class BoundaryCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    left_element_id: str
    right_element_id: str
    left_type: str
    right_type: str
    left_parent_id: str | None = None
    right_parent_id: str | None = None
    accumulated_char_count: int
    right_char_count: int


class BoundaryFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hierarchy_continuity: bool
    heading_continuity: bool
    section_continuity: bool
    structural_compatibility: bool
    lexical_continuity: bool
    table_integrity: bool
    list_integrity: bool
    code_integrity: bool
    quote_integrity: bool
    layout_continuity: bool
    size_budget: SizeBudgetStatus


class BoundaryDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["merge", "split"]
    applied_rule: str
    triggered_features: list[str]
    rationale: str

    @field_validator("triggered_features")
    @classmethod
    def _non_empty_features(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("triggered_features must be non-empty")
        return value


class ChunkLineage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_element_ids: list[str]
    applied_rule: str
    triggered_features: list[str]
    rationale: str
    oversized_split_index: int | None = None


class StructuralContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    element_type: str
    heading_path: list[str] = Field(default_factory=list)
    position: int = 0


class ChunkIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    document_id: str
    strategy_id: str
    source_element_ids: list[str]


class ChunkRelationships(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_chunk_id: str | None = None
    previous_chunk_id: str | None = None
    next_chunk_id: str | None = None
    child_chunk_ids: list[str] = Field(default_factory=list)


class Chunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    identity: ChunkIdentity | None = None
    relationships: ChunkRelationships = Field(default_factory=ChunkRelationships)
    lineage: ChunkLineage | None = None
    structural_context: StructuralContext | None = None


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ValidationStatus
    failed_rules: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    validation_messages: list[str] = Field(default_factory=list)


class ChunkSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunks: list[Chunk] = Field(default_factory=list)
    validation_report: ValidationReport
    asset_id: str
    strategy_id: str
    element_counts_by_type: dict[str, int] = Field(default_factory=dict)


class ChunkingStrategyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str = "semantic_structural"
    max_chars: int = 800
    overlap: int = 0
    policy: str = "rule_based"
    element_mapping: dict[str, ElementChunkConfig] = Field(default_factory=dict)


def compute_config_hash(config: ChunkingStrategyConfig) -> str:
    """Stable fingerprint for strategy configuration (research R2)."""
    payload = json.dumps(config.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]
