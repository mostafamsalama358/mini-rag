"""Evidence Orchestrator domain models."""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.retrieval_engine.models import RetrievedCandidate

SCHEMA_VERSION = "1.0.0"
ORCHESTRATOR_VERSION = "1.0.0"

StageName = Literal[
    "collect",
    "deduplicate",
    "expand",
    "compress_flag",
    "prioritize",
    "package",
]
DedupMethod = Literal["exact_only", "embedding", "character_ngram"]


def _sha16(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def compute_item_id(chunk_id: str, doc_id: str) -> str:
    return "ei_" + _sha16(f"{chunk_id}|{doc_id}")


def compute_pack_id(plan_id: str, created_at: str) -> str:
    return "ep_" + _sha16(f"{plan_id}|{created_at}")


class Citation(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    retrieval_score: float = Field(ge=0.0)
    score_source: str
    page_number: int | None = None
    section_title: str | None = None
    document_title: str | None = None
    chunk_index: int | None = None


class EvidenceItemSource(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy_id: str = Field(min_length=1)
    raw_score: float


class EvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    doc_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    section_path: list[str] = Field(default_factory=list)
    entity_tags: list[str] = Field(default_factory=list)
    relation_tags: list[str] = Field(default_factory=list)
    citation: Citation
    text: str = Field(min_length=1)
    relevance_score: float = Field(ge=0.0, le=1.0)
    compressibility_score: float = Field(ge=0.0, le=1.0, default=0.0)
    sources: list[EvidenceItemSource] = Field(min_length=1)
    expanded: bool = False

    @field_validator("item_id")
    @classmethod
    def _item_id_prefix(cls, value: str) -> str:
        if not value.startswith("ei_"):
            raise ValueError("item_id must start with 'ei_'")
        return value


class CollectedItem(BaseModel):
    """Internal intermediate model produced by the Collect stage."""

    model_config = ConfigDict(frozen=True)

    candidate: RetrievedCandidate
    strategy_id: str = Field(min_length=1)
    raw_token_count: int = Field(ge=0)
    contributing_sources: list[EvidenceItemSource] = Field(min_length=1)
    text: str | None = None
    expanded: bool = False

    @property
    def effective_text(self) -> str:
        if self.text is not None and self.text.strip():
            return self.text
        return self.candidate.content_excerpt or ""


class OrchestratorStageTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage: StageName
    input_count: int = Field(ge=0)
    output_count: int = Field(ge=0)
    latency_ms: float = Field(ge=0.0)


class OrchestratorTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    orchestrator_version: str = ORCHESTRATOR_VERSION
    stages: list[OrchestratorStageTrace] = Field(default_factory=list)
    total_latency_ms: float = Field(ge=0.0, default=0.0)
    dedup_method_used: DedupMethod = "exact_only"
    expansion_enabled: bool = True


class EvidencePack(BaseModel):
    model_config = ConfigDict(frozen=True)

    pack_id: str
    plan_id: str = Field(min_length=1)
    schema_version: str = SCHEMA_VERSION
    items: list[EvidenceItem] = Field(default_factory=list)
    is_empty: bool
    strategies_used: list[str] = Field(default_factory=list)
    token_reduction_ratio: float | None = None
    raw_candidate_count: int = Field(ge=0)
    trace: OrchestratorTrace
    created_at: str

    @field_validator("pack_id")
    @classmethod
    def _pack_id_prefix(cls, value: str) -> str:
        if not value.startswith("ep_"):
            raise ValueError("pack_id must start with 'ep_'")
        return value

    @model_validator(mode="after")
    def _is_empty_consistent(self) -> EvidencePack:
        if self.is_empty != (len(self.items) == 0):
            raise ValueError("is_empty must equal (len(items) == 0)")
        return self

    @field_validator("token_reduction_ratio")
    @classmethod
    def _token_ratio_range(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if value <= 0.0 or value > 1.0:
            raise ValueError("token_reduction_ratio must be in (0.0, 1.0]")
        return value
