"""Immutable Skill execution unit passed through the sole answer path (021/022)."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Literal

from core.query_parser.schema import QueryPlan
from fields.schemas import SkillDefinition, SkillFilterProfile, SkillValidationRules
from services.rag.skills.filters import effective_filters

RetrievalStrategyName = Literal[
    "default",
    "pair_lookup",
    "document_lookup",
    "semantic_only",
    "hybrid",
]

_STRATEGY_DEFAULT_OPERATION: dict[str, str] = {
    "default": "lookup",
    "pair_lookup": "list",
    "document_lookup": "explain",
    "semantic_only": "lookup",
    "hybrid": "lookup",
}


def _derive_plan_field(profile: SkillFilterProfile) -> str:
    fields = list(profile.filters.field or [])
    return fields[0] if fields else "unknown"


def _derive_plan_operation(
    profile: SkillFilterProfile,
    *,
    recommend_mode: bool,
) -> str:
    if recommend_mode:
        return "recommend"
    return _STRATEGY_DEFAULT_OPERATION.get(profile.retrieval_strategy, "lookup")


@dataclass(frozen=True)
class SkillExecutionContext:
    """Single immutable execution object for a Skill-bound request."""

    skill: SkillDefinition
    profile: SkillFilterProfile
    metadata_filters: dict[str, Any]
    prompt_ref: str
    validation: SkillValidationRules
    retrieval_strategy: RetrievalStrategyName
    response_schema: dict[str, Any] | str | None
    citation_policy: str | None
    domain_key: str
    skill_id: str
    entities: tuple[str, ...] = ()
    slots: dict[str, Any] = field(default_factory=dict)
    need_text: str | None = None
    recommend_mode: bool = False

    @classmethod
    def from_skill_and_profile(
        cls,
        *,
        skill: SkillDefinition,
        profile: SkillFilterProfile,
        domain_key: str,
    ) -> "SkillExecutionContext":
        recommend = bool(skill.capabilities.recommend_mode)
        strategy = profile.retrieval_strategy
        if isinstance(skill.retrieval, dict) and skill.retrieval.get("strategy"):
            strategy = str(skill.retrieval["strategy"])  # type: ignore[assignment]
        return cls(
            skill=skill,
            profile=profile,
            metadata_filters=effective_filters(profile),
            prompt_ref=(skill.prompt or skill.id).strip() or skill.id,
            validation=skill.validation,
            retrieval_strategy=strategy,  # type: ignore[arg-type]
            response_schema=skill.response_schema,
            citation_policy=skill.citation_policy,
            domain_key=domain_key,
            skill_id=skill.id,
            recommend_mode=recommend,
        )

    def with_entities(
        self,
        entities: list[str] | tuple[str, ...],
        *,
        slots: dict[str, Any] | None = None,
        need_text: str | None = None,
    ) -> "SkillExecutionContext":
        cleaned = tuple(
            dict.fromkeys(str(e).strip() for e in entities if e and str(e).strip())
        )
        return replace(
            self,
            entities=cleaned,
            slots=dict(slots or {}),
            need_text=need_text,
        )

    @property
    def primary_entity(self) -> str | None:
        return self.entities[0] if self.entities else None

    @property
    def suppress_entity_scoped_search(self) -> bool:
        """Strategy hint: pair lookup owns entity scoping via structured fetch."""
        return self.retrieval_strategy == "pair_lookup"

    @property
    def skip_entity_grounding(self) -> bool:
        """Strategy hint: structured pair results skip post-retrieval grounding."""
        return self.retrieval_strategy == "pair_lookup"

    @property
    def prefers_exhaustive_retrieval(self) -> bool:
        """Strategy hint: widen retrieval limit for exhaustive pair/list flows."""
        return self.retrieval_strategy == "pair_lookup"

    def build_query_plan(self, *, language: str = "en") -> QueryPlan:
        """Build QueryPlan from Skill context + entities — transitional bridge only."""
        entity = self.primary_entity
        plan_field = _derive_plan_field(self.profile)
        plan_operation = _derive_plan_operation(
            self.profile,
            recommend_mode=self.recommend_mode,
        )
        return QueryPlan(
            entity=entity,
            entities=list(self.entities),
            field=plan_field,
            operation=plan_operation,  # type: ignore[arg-type]
            scope="all" if plan_operation == "list" else "single",
            language=(language or "en")[:2],
            recommend_mode=self.recommend_mode,
            needs_clarification=False,
            clarification_prompt=None,
            filters=dict(self.metadata_filters),
        )

    def merge_client_filters(self, base: dict[str, Any] | None) -> dict[str, Any]:
        merged = dict(base or {})
        for key, value in self.metadata_filters.items():
            if key == "extra" and isinstance(value, dict):
                merged.update(value)
            else:
                merged[key] = value
        return merged
