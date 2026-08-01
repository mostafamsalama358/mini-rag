"""Deprecated apply helpers — SkillExecutionContext.build_query_plan is canonical."""

from __future__ import annotations

from core.query_parser.schema import QueryPlan
from services.rag.skills.context import SkillExecutionContext


def apply_skill_to_query_plan(
    query_plan: QueryPlan,
    binding: SkillExecutionContext,
) -> QueryPlan:
    """Legacy helper: rebuild plan from Skill context, preserving language/entities if present."""
    entities = list(binding.entities) or list(query_plan.entities or [])
    if query_plan.entity and query_plan.entity not in entities:
        entities.insert(0, query_plan.entity)
    ctx = binding.with_entities(entities, need_text=binding.need_text, slots=binding.slots)
    return ctx.build_query_plan(language=query_plan.language)


def entities_from_plan(query_plan: QueryPlan) -> list[str]:
    ents: list[str] = []
    if query_plan.entities:
        ents.extend(query_plan.entities)
    if query_plan.entity:
        ents.append(query_plan.entity)
    return ents
