"""Retrieval Planner domain models — the stable public RetrievalPlan contract."""

from __future__ import annotations

import hashlib
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

# ---------------------------------------------------------------------------
# Open types and enumerations (§0)
# ---------------------------------------------------------------------------

StrategyType = Annotated[str, Field(min_length=1)]

IntentCategory = Literal[
    "factual",
    "list",
    "comparative",
    "procedural",
    "tabular",
    "navigational",
    "mixed",
]

OutputShapeType = Literal[
    "single_fact",
    "list",
    "summary",
    "table",
    "comparison",
    "narrative",
]

_FILTER_OPERATORS = frozenset(
    {"eq", "neq", "lt", "gt", "lte", "gte", "in", "not_in", "contains", "range"}
)

SCHEMA_VERSION = "1.0.0"
PLANNER_VERSION = "1.0.0"

_DEFAULT_AVAILABLE_STRATEGIES: list[str] = [
    "semantic",
    "keyword",
    "metadata",
    "graph",
    "document",
    "section",
    "table",
    "hybrid",
    "mixed",
]

_DEFAULT_STRATEGY_MAPPINGS: dict[str, list[str]] = {
    "factual": ["semantic", "hybrid"],
    "list": ["semantic", "keyword"],
    "comparative": ["semantic", "hybrid", "graph"],
    "procedural": ["semantic", "document"],
    "tabular": ["table", "semantic"],
    "navigational": ["metadata", "document"],
    "mixed": ["hybrid", "semantic", "keyword"],
}

_DEFAULT_BUDGET_DEFAULTS: dict[str, Any] = {
    "factual": {"scope": "narrow", "max_evidence_units": 5, "max_candidates": 20},
    "list": {"scope": "standard", "max_evidence_units": 10, "max_candidates": 40},
    "comparative": {"scope": "standard", "max_evidence_units": 8, "max_candidates": 30},
    "procedural": {"scope": "standard", "max_evidence_units": 8, "max_candidates": 30},
    "tabular": {"scope": "narrow", "max_evidence_units": 3, "max_candidates": 10},
    "navigational": {"scope": "narrow", "max_evidence_units": 3, "max_candidates": 15},
    "mixed": {"scope": "broad", "max_evidence_units": 15, "max_candidates": 60},
}


def _sha16(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def compute_filter_id(
    filter_type: str,
    field_name: str,
    operator: str,
    value: Any,
) -> str:
    return "flt_" + _sha16(f"{filter_type}|{field_name}|{operator}|{str(value)}")


def compute_entity_id(canonical_form: str, entity_type: str) -> str:
    return "ent_" + _sha16(f"{canonical_form}|{entity_type}")


def compute_config_hash(config: RetrievalPlannerConfig) -> str:
    payload = (
        f"{sorted(config.available_strategies)}"
        f"|{config.default_strategy}"
        f"|{config.clarification_confidence_threshold}"
        f"|{sorted(config.strategy_mappings.items())}"
        f"|{sorted((k, str(v)) for k, v in config.budget_defaults.items())}"
        f"|{config.citation_required}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


def compute_plan_id(
    canonical_query: str,
    intent_category: str,
    strategies: tuple[str, ...] | list[str],
    config_hash: str,
) -> str:
    sorted_strats = "|".join(sorted(strategies))
    payload = f"{canonical_query}|{intent_category}|{sorted_strats}|{config_hash}"
    return "rp_" + _sha16(payload)


# ---------------------------------------------------------------------------
# Primary value models (§1–3, §7)
# ---------------------------------------------------------------------------


class QueryIntent(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: IntentCategory
    confidence: float = Field(ge=0.0, le=1.0)
    secondary_categories: tuple[IntentCategory, ...] = ()
    evidence: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _no_self_secondary(self) -> QueryIntent:
        if self.category in self.secondary_categories:
            raise ValueError("secondary_categories must not contain category")
        return self


class ResolvedEntity(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity_id: str
    raw_text: str = Field(min_length=1)
    canonical_form: str = Field(min_length=1)
    entity_type: str
    source_span: tuple[int, int] | None = None


class QueryFilter(BaseModel):
    model_config = ConfigDict(frozen=True)

    filter_id: str
    filter_type: str
    field_name: str = Field(min_length=1)
    operator: str
    value: Any
    source: Literal["explicit", "implicit"]

    @field_validator("operator")
    @classmethod
    def _valid_operator(cls, value: str) -> str:
        if value not in _FILTER_OPERATORS:
            raise ValueError(f"unsupported operator: {value!r}")
        return value


class OutputShape(BaseModel):
    model_config = ConfigDict(frozen=True)

    shape_type: OutputShapeType
    max_items: int | None = Field(default=None, ge=1)
    structured: bool


# ---------------------------------------------------------------------------
# Execution contract models (§4–6)
# ---------------------------------------------------------------------------


class RetrievalLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_evidence_units: int = Field(ge=1)
    max_candidates: int
    scope: Literal["narrow", "standard", "broad", "exhaustive"]

    @model_validator(mode="after")
    def _candidates_gte_units(self) -> RetrievalLimits:
        if self.max_candidates < self.max_evidence_units:
            raise ValueError("max_candidates must be >= max_evidence_units")
        return self


class RetrievalConstraints(BaseModel):
    model_config = ConfigDict(frozen=True)

    latency_budget_ms: int | None = Field(default=None, ge=1)
    cost_budget: float | None = None
    freshness_window: str | None = None
    required_language: str | None = None
    citation_required: bool = True

    @field_validator("required_language")
    @classmethod
    def _lang_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        lang = value.strip().lower()
        if len(lang) != 2 or not lang.isalpha():
            raise ValueError("required_language must be a 2-letter ISO 639-1 code")
        return lang


class ExecutionHints(BaseModel):
    """Built incrementally; frozen when embedded in RetrievalPlan."""

    model_config = ConfigDict(frozen=False)

    preferred_document_types: list[str] | None = None
    preferred_section_kinds: list[str] | None = None
    expand_entities: bool | None = None
    allow_table_search: bool | None = None
    prioritize_recent_content: bool | None = None


# ---------------------------------------------------------------------------
# Internal and identity models (§8–9)
# ---------------------------------------------------------------------------


class PlannerDiagnostics(BaseModel):
    """Internal debugging metadata — not frozen; omitted in production."""

    model_config = ConfigDict(frozen=False)

    intent_candidates: list[dict[str, Any]] = Field(default_factory=list)
    entity_resolution_trace: list[dict[str, Any]] = Field(default_factory=list)
    strategy_selection_trace: list[dict[str, Any]] = Field(default_factory=list)
    clarification_trigger: str | None = None
    limits_derivation: dict[str, Any] = Field(default_factory=dict)
    planning_latency_ms: float = 0.0


class RetrievalPlanMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_id: str
    planner_version: str
    schema_version: str
    config_hash: str
    created_at: str


# ---------------------------------------------------------------------------
# RetrievalPlan (§10)
# ---------------------------------------------------------------------------


class RetrievalPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    canonical_query: str = ""
    intent: QueryIntent
    entities: tuple[ResolvedEntity, ...] = ()
    filters: tuple[QueryFilter, ...] = ()
    retrieval_strategies: tuple[str, ...] = ()
    retrieval_limits: RetrievalLimits
    retrieval_constraints: RetrievalConstraints
    execution_hints: ExecutionHints | None = None
    output_shape: OutputShape
    clarification_required: bool
    clarification_question: str | None = None
    planner_confidence: float = Field(ge=0.0, le=1.0)
    diagnostics: PlannerDiagnostics | None = None
    metadata: RetrievalPlanMetadata

    @model_validator(mode="after")
    def _clarification_invariants(self) -> RetrievalPlan:
        if self.clarification_required:
            if not (self.clarification_question or "").strip():
                raise ValueError(
                    "clarification_question required when clarification_required=True"
                )
            if self.retrieval_strategies:
                raise ValueError(
                    "retrieval_strategies must be empty when clarification_required=True"
                )
        else:
            if not self.retrieval_strategies:
                raise ValueError(
                    "retrieval_strategies must be non-empty when clarification_required=False"
                )
            if self.clarification_question is not None:
                raise ValueError(
                    "clarification_question must be None when clarification_required=False"
                )
        return self


# ---------------------------------------------------------------------------
# RetrievalPlannerConfig (§11)
# ---------------------------------------------------------------------------


class RetrievalPlannerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_classifier: str = "rule_based"
    entity_resolver: str = "query_plan"
    filter_extractor: str = "query_plan"
    strategy_selector: str = "config_driven"
    clarification_detector: str = "confidence_based"
    available_strategies: list[str] = Field(
        default_factory=lambda: list(_DEFAULT_AVAILABLE_STRATEGIES)
    )
    default_strategy: str = "semantic"
    clarification_confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    strategy_mappings: dict[str, list[str]] = Field(
        default_factory=lambda: {k: list(v) for k, v in _DEFAULT_STRATEGY_MAPPINGS.items()}
    )
    budget_defaults: dict[str, Any] = Field(
        default_factory=lambda: {k: dict(v) for k, v in _DEFAULT_BUDGET_DEFAULTS.items()}
    )
    entity_aliases: dict[str, str] = Field(default_factory=dict)
    entity_type_patterns: list[dict[str, str]] = Field(default_factory=list)
    default_latency_budget_ms: int | None = None
    default_cost_budget: float | None = None
    citation_required: bool = True
    diagnostics_enabled: bool = False
    # Optional ceiling applied across all intents (field-pack override).
    max_evidence_units_ceiling: int | None = None
