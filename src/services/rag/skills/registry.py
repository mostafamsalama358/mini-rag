"""Skill registry resolution — exact id lookup; builds SkillExecutionContext."""

from __future__ import annotations

from typing import Any

from fields.schemas import SkillDefinition
from services.FieldRegistry import FieldProfile
from services.rag.skills.context import SkillExecutionContext


class SkillResolutionError(ValueError):
    """Raised when skill_id cannot be resolved for the active domain."""

    def __init__(self, message: str, *, code: str = "unknown_skill") -> None:
        super().__init__(message)
        self.code = code


def skill_registry_required(profile: FieldProfile) -> bool:
    return bool(getattr(profile, "skills", None))


def list_skill_catalog(profile: FieldProfile) -> list[dict[str, Any]]:
    """Ordered Skill catalog for UI/API."""
    skills: dict[str, SkillDefinition] = getattr(profile, "skills", None) or {}
    ordered = sorted(
        skills.values(),
        key=lambda s: (s.order if s.order is not None else 999, s.id),
    )
    catalog: list[dict[str, Any]] = []
    for skill in ordered:
        item: dict[str, Any] = {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
        }
        if skill.subject:
            item["subject"] = skill.subject
            item["subject_label"] = skill.subject_label or skill.subject
            if skill.intent:
                item["intent"] = skill.intent
        catalog.append(item)
    return catalog


def resolve_skill(
    profile: FieldProfile,
    skill_id: str | None,
) -> SkillExecutionContext | None:
    """Resolve client skill_id into SkillExecutionContext (None if pack has no skills)."""
    skills = getattr(profile, "skills", None) or {}
    if not skills:
        return None

    normalized = (skill_id or "").strip()
    if not normalized:
        raise SkillResolutionError(
            "Skill selection is required for this domain. Choose a Skill before asking.",
            code="skill_required",
        )

    skill = skills.get(normalized)
    if skill is None:
        raise SkillResolutionError(
            f"Unknown skill_id '{normalized}' for domain '{profile.domain_key}'.",
            code="unknown_skill",
        )

    skill_profile = profile.skill_profiles.get(skill.profile)
    if skill_profile is None:
        raise SkillResolutionError(
            f"Skill '{normalized}' references missing profile '{skill.profile}'.",
            code="missing_profile",
        )

    return SkillExecutionContext.from_skill_and_profile(
        skill=skill,
        profile=skill_profile,
        domain_key=profile.domain_key,
    )
