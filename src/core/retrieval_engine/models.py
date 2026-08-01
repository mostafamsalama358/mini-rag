"""Retrieval Engine domain models — stable RetrievalResult contract."""

from __future__ import annotations

import hashlib
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.retrieval_engine.policies import ExecutionPolicy
from core.retrieval_planner.models import (
    ExecutionHints,
    QueryFilter,
    RetrievalConstraints,
    StrategyType,
)

SCHEMA_VERSION = "1.0.0"
EXPECTED_SCHEMA_MAJOR = 1

ScoreSource = Literal["reranker", "fusion", "raw"]
FusionAlgorithm = Literal["rrf", "passthrough"]
SkipReason = Annotated[str, Field(min_length=1)]


def _sha16(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def compute_result_id(
    plan_id: str,
    strategies: tuple[str, ...] | list[str],
    fusion_algorithm: str,
    reranker_id: str,
) -> str:
    sorted_strats = "|".join(sorted(strategies))
    payload = f"{plan_id}|{sorted_strats}|{fusion_algorithm}|{reranker_id}"
    return "rr_" + _sha16(payload)


class SourceRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    chunk_id: str
    page_number: int | None = None
    section_title: str | None = None
    chunk_index: int | None = None
    document_title: str | None = None


class RetrievalQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    query_text: str
    strategy: StrategyType
    expander_variant_id: str


class RetrievalContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_id: str
    filters: tuple[QueryFilter, ...] = ()
    constraints: RetrievalConstraints | None = None
    hints: ExecutionHints | None = None
    policy: ExecutionPolicy
    # Adapter scope: collection_name, project_id, entity_key, entity_prefix,
    # field_key, metadata_filter, limit, etc. (spec 015 adapters contract).
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExpansionContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    query_text: str
    intent_category: str | None = None
    entities: tuple[str, ...] = ()
    language: str | None = None
    max_variants: int = 3


class ExpansionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    variants: tuple[str, ...]
    expansion_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("variants")
    @classmethod
    def _min_one_variant(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) < 1:
            raise ValueError("variants must contain at least one entry")
        return value


class RawCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    document_id: str
    raw_score: float
    retriever_id: str
    strategy: str
    expander_variant_id: str
    content_excerpt: str = ""
    source_ref: SourceRef | None = None


class RetrievedCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    document_id: str
    score: float
    score_source: ScoreSource
    source_ref: SourceRef | None = None
    content_excerpt: str = ""
    rank: int = Field(ge=1)


class RetrievalStepTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    step_index: int
    strategy: str
    expander_variant_id: str
    retriever_id: str | None = None
    raw_count: int = 0
    post_filter_count: int = 0
    latency_ms: float = 0.0
    retry_count: int = 0
    skipped: bool = False
    skip_reason: str | None = None
    error: str | None = None


class RetrievalTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_id: str
    steps: tuple[RetrievalStepTrace, ...] = ()
    total_latency_ms: float = 0.0
    constraint_violations: tuple[str, ...] = ()


class RetrievalExecutionMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    result_id: str
    plan_id: str
    schema_version: str = SCHEMA_VERSION
    executed_strategies: tuple[str, ...] = ()
    hybrid_components_used: tuple[str, ...] = ()
    fusion_algorithm: FusionAlgorithm = "rrf"
    reranker_used: bool = False
    expander_used: bool = False
    expander_type: str = "passthrough"
    total_latency_ms: float = 0.0


class RetrievalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    result_id: str
    plan_id: str
    candidates: tuple[RetrievedCandidate, ...] = ()
    trace: RetrievalTrace
    metadata: RetrievalExecutionMetadata
    partial: bool = False
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def _ids_consistent(self) -> RetrievalResult:
        if self.result_id != self.metadata.result_id:
            raise ValueError("result_id must match metadata.result_id")
        if self.plan_id != self.metadata.plan_id:
            raise ValueError("plan_id must match metadata.plan_id")
        return self


class RetrievalEngineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled_strategies: list[str] = Field(
        default_factory=lambda: [
            "semantic",
            "keyword",
            "metadata",
            "structured",
            "mixed",
        ]
    )
    hybrid_components: list[str] = Field(
        default_factory=lambda: ["semantic", "keyword"]
    )
    default_strategy: str = "semantic"
    fusion_algorithm: FusionAlgorithm = "rrf"
    rrf_k: int = 60
    reranker_backend: str = "passthrough"
    max_expander_variants: int = 3
    trace_enabled: bool = True
    partial_results_allowed: bool = True
    budget_defaults: dict[str, Any] = Field(
        default_factory=lambda: {"max_candidates": 50, "max_evidence_units": 10}
    )
