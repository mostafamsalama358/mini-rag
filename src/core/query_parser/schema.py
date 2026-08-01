"""QueryPlan, ConversationContext, and ParseResult models."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.query_parser.need_frame import NeedFrame

OperationEnum = Literal[
    "lookup",
    "list",
    "compare",
    "explain",
    "count",
    "recommend",
    "unsupported",
]
ScopeEnum = Literal["all", "single", "subset"]


class QueryPlan(BaseModel):
    """Structured retrieval intent consumed by the retriever.

    Feature 020 adds optional recommend_mode + need_frame (additive; existing
    callers remain valid). recommend is NOT a new production API owner.
    """

    model_config = ConfigDict(extra="forbid")

    entity: str | None = None
    entities: list[str] = Field(default_factory=list)
    field: str
    operation: OperationEnum
    scope: ScopeEnum
    language: str
    filters: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    needs_clarification: bool = False
    clarification_prompt: str | None = None
    recommend_mode: bool = False
    need_frame: NeedFrame | None = None

    @field_validator("language")
    @classmethod
    def _validate_language(cls, value: str) -> str:
        lang = (value or "").strip().lower()
        if len(lang) != 2 or not lang.isalpha():
            raise ValueError("language must be a two-letter ISO 639-1 code")
        return lang

    @model_validator(mode="after")
    def _clarification_prompt_required(self) -> "QueryPlan":
        if self.needs_clarification and not (self.clarification_prompt or "").strip():
            raise ValueError("clarification_prompt is required when needs_clarification=true")
        return self


class TurnSummary(BaseModel):
    """One prior chat turn for parser context."""

    model_config = ConfigDict(extra="forbid")

    user_text: str
    canonical_query: str | None = None
    query_plan: QueryPlan | None = None


class ConversationContext(BaseModel):
    """Bounded session context passed to the semantic parser."""

    model_config = ConfigDict(extra="forbid")

    current_entity: str | None = None
    recent_turns: list[TurnSummary] = Field(default_factory=list)
    document_language: str = "en"
    project_domain: str = "generic"


class ParseResult(BaseModel):
    """Output of semantic_parse_async."""

    model_config = ConfigDict(extra="forbid")

    original_query: str
    canonical_query: str
    query_plan: QueryPlan
    used_llm: bool
    latency_ms: float
    grounding_score: float | None = None
    error: str | None = None
