"""Skill validation rules — clarify on failure; never switch Skill (021)."""

from __future__ import annotations

from fields.schemas import SkillDefinition


def evaluate_skill_validation(
    skill: SkillDefinition,
    entities: list[str] | None,
    *,
    has_need_frame: bool = False,
) -> tuple[bool, str | None]:
    """Return (ok, clarification_prompt|None) for entity/slot validation."""
    rules = skill.validation
    grounded = [str(e).strip() for e in (entities or []) if e and str(e).strip()]
    distinct = list(dict.fromkeys(grounded))

    if rules.require_medicine_pair and len(distinct) < 2:
        return False, "Please name two medicines to check for interactions."

    if rules.require_medicine and not rules.require_medicine_pair and len(distinct) < 1:
        return False, "Please name the medicine you are asking about."

    if rules.require_need and not has_need_frame:
        return False, "Please describe what you need help finding."

    if rules.min_entities is not None and len(distinct) < rules.min_entities:
        return False, f"Please provide at least {rules.min_entities} item(s)."

    if rules.max_entities is not None and len(distinct) > rules.max_entities:
        return False, f"Please provide at most {rules.max_entities} item(s)."

    return True, None
