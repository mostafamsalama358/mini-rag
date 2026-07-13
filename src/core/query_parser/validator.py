"""Field-registry validation for QueryPlan."""
from __future__ import annotations

from fields.schemas import FieldRegistryProfile, ParserProfile

from .schema import QueryPlan


def validate_query_plan(
    plan: QueryPlan,
    field_registry: FieldRegistryProfile,
    *,
    parser_profile: ParserProfile | None = None,
) -> QueryPlan:
    """Ensure plan.field is allowed; coerce unknown fields to clarification."""
    if plan.needs_clarification:
        return plan

    if plan.field == "unknown":
        return plan

    allowed: set[str] = set()
    if parser_profile and parser_profile.allowed_fields:
        allowed = {f.strip() for f in parser_profile.allowed_fields if f.strip()}
    else:
        allowed = {c.concept for c in field_registry.concepts}

    if plan.field in allowed:
        return plan

    return plan.model_copy(
        update={
            "field": "unknown",
            "needs_clarification": True,
            "clarification_prompt": (
                f"I could not map your question to a supported topic "
                f"('{plan.field}'). Please rephrase or name a specific item."
            ),
        }
    )
