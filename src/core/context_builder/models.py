"""Context Builder domain models."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.evidence_orchestrator.models import Citation

SCHEMA_VERSION = "1.0.0"


def _sha16(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def compute_context_id(pack_id: str, created_at: str) -> str:
    return "ctx_" + _sha16(f"{pack_id}|{created_at}")


class ContextBlock(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    section_path: str | None = None
    text: str = Field(min_length=1)
    token_count: int = Field(ge=1)
    compressed: bool = False


class ConflictGroup(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity_tag: str = Field(min_length=1)
    attribute: str = Field(min_length=1)
    item_ids: list[str] = Field(min_length=2)
    resolution: str | None = None


class ContextMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    items_included: int = Field(ge=0)
    items_dropped: int = Field(ge=0)
    items_compressed: int = Field(ge=0)
    conflicts_detected: bool = False
    budget_total: int = Field(ge=0)
    budget_used: int = Field(ge=0)
    timeout: bool = False


class Context(BaseModel):
    model_config = ConfigDict(frozen=True)

    context_id: str
    pack_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    schema_version: str = SCHEMA_VERSION
    ordered_blocks: list[ContextBlock] = Field(default_factory=list)
    citation_map: dict[str, Citation] = Field(default_factory=dict)
    token_count: int = Field(ge=0)
    conflicts: list[ConflictGroup] = Field(default_factory=list)
    metadata: ContextMetadata
    created_at: str

    @field_validator("context_id")
    @classmethod
    def _context_id_prefix(cls, value: str) -> str:
        if not value.startswith("ctx_"):
            raise ValueError("context_id must start with 'ctx_'")
        return value

    @model_validator(mode="after")
    def _citation_completeness(self) -> Context:
        block_ids = {block.item_id for block in self.ordered_blocks}
        citation_ids = set(self.citation_map.keys())
        if block_ids != citation_ids:
            raise ValueError(
                "ordered_blocks item_ids must match citation_map keys exactly"
            )
        return self

    @model_validator(mode="after")
    def _token_count_sum(self) -> Context:
        expected = sum(block.token_count for block in self.ordered_blocks)
        if self.token_count != expected:
            raise ValueError(
                f"token_count ({self.token_count}) must equal sum of block "
                f"token counts ({expected})"
            )
        return self


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
