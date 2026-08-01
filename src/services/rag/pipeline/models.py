"""Orchestration-boundary models for the unified pipeline migration (spec 015)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from models.enums.ResponseEnums import ResponseSignal

PipelineMode = Literal["legacy", "shadow", "unified"]

PipelineOutcome = Literal[
    "success",
    "clarification",
    "no_context",
    "scope_miss",
    "field_unavailable",
    "error",
    "timeout",
]

StageStatus = Literal[
    "pending",
    "running",
    "completed",
    "failed",
    "skipped",
    "timed_out",
]

StageName = Literal["parse", "plan", "retrieve", "evidence", "context", "answer"]


class PipelineSettingsSnapshot(BaseModel):
    """Frozen pipeline flags effective for one request."""

    model_config = ConfigDict(frozen=True)

    pipeline_mode: PipelineMode
    fallback_on_error: bool
    unified_timeout_s: float
    hybrid_search_enabled: bool
    reranker_enabled: bool
    semantic_parser_enabled: bool


class PipelineExecutionContext(BaseModel):
    """Immutable per-request context threaded through router and orchestrator."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    request_id: str
    project_id: int
    session_id: str | None = None
    mode: PipelineMode
    profile: Any  # FieldProfile — arbitrary to avoid circular imports
    metadata_filter: dict[str, Any] | None = None
    limit: int
    locale: str
    started_at: float
    deadline_at: float
    pipeline_version: str
    settings_snapshot: PipelineSettingsSnapshot
    skill_ctx: Any | None = None
    skill_id: str | None = None


class PipelineStageTrace(BaseModel):
    """Per-stage telemetry for one request."""

    model_config = ConfigDict(frozen=True)

    stage: StageName
    status: StageStatus
    started_at: float
    duration_ms: float
    outcome: str | None = None  # deprecated alias for status
    plan_id: str | None = None
    context_id: str | None = None
    error_type: str | None = None
    detail: dict[str, Any] | None = None


class UnifiedPipelineResult(BaseModel):
    """Output of UnifiedRagOrchestrator before API adaptation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    execution_context: PipelineExecutionContext
    parse_result: Any | None = None  # ParseResult
    retrieval_plan: Any | None = None  # RetrievalPlan
    retrieval_result: Any | None = None  # engine RetrievalResult
    evidence_pack: Any | None = None  # EvidencePack
    built_context: Any | None = None  # Context (012) — avoid shadowing execution context
    answer_result: Any | None = None  # AnswerResult
    stage_traces: list[PipelineStageTrace] = Field(default_factory=list)
    outcome: PipelineOutcome = "error"
    # Feature 020 — internal recommend artifacts (not frozen /answer fields)
    recommend_decision: Any | None = None
    recommend_trace: Any | None = None


class PipelineAnswerResponse(BaseModel):
    """Internal representation mapping 1:1 to the frozen /answer JSON contract."""

    model_config = ConfigDict(frozen=True)

    answer: str | None = None
    full_prompt: str | None = None
    chat_history: list | None = None
    needs_clarification: bool = False
    signal: ResponseSignal = ResponseSignal.RAG_ANSWER_SUCCESS


class ShadowComparisonRecord(BaseModel):
    """Persisted JSONL artifact for shadow dual-run diagnostics."""

    model_config = ConfigDict(frozen=True)

    request_id: str
    project_id: int
    mode: Literal["shadow"] = "shadow"
    recorded_at: str
    query_text: str
    legacy_outcome: PipelineOutcome
    unified_outcome: PipelineOutcome
    legacy_answer: str | None = None
    unified_answer: str | None = None
    answer_similarity: float | None = None
    diverged: bool = False
    legacy_latency_ms: float = 0.0
    unified_latency_ms: float | None = None
    unified_plan_id: str | None = None
    legacy_citation_count: int = 0
    unified_citation_count: int = 0
    unified_error: str | None = None
    first_divergent_stage: str | None = None
    plan_strategy_match: bool | None = None
    retrieval_overlap: float | None = None
    evidence_overlap: float | None = None
    context_token_delta: int | None = None
