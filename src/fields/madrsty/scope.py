"""Madrsty retrieval scope. Lives in the domain pack, not the shared answer path.

Answer and search stay domain-agnostic. The route loads
``fields.{domain}.scope.check_retrieval_scope`` when that module exists.
"""

from __future__ import annotations

from typing import Any, Literal

RouteName = Literal["answer", "search"]


class MadrstyScopeError(ValueError):
    """Raised when a Madrsty request is missing a valid grade or subject scope."""


def _domain_key(project) -> str:
    raw = getattr(project, "domain_key", None)
    return str(getattr(raw, "value", raw) or "").lower()


def validate_madrsty_retrieval_scope(
    *,
    domain_key: str | None,
    classes: list[dict[str, Any]] | None,
    metadata_filter: dict[str, Any] | None,
    route: RouteName,
    skill_subject: str | None = None,
) -> None:
    """Reject an unscoped Madrsty query before any vector search.

    Other domains are ignored. ``grade`` must be a ``classes.yaml`` id on both
    answer and search. Search also requires a subject of that class. Answer
    rejects a client ``subject`` that disagrees with the selected skill.
    """
    if str(domain_key or "").strip().lower() != "madrsty":
        return

    catalog: dict[str, dict[str, Any]] = {}
    for item in classes or []:
        if isinstance(item, dict) and item.get("id"):
            catalog[str(item["id"])] = item

    filt = metadata_filter if isinstance(metadata_filter, dict) else {}
    grade = str(filt.get("grade") or "").strip()
    if not grade or grade not in catalog:
        raise MadrstyScopeError(
            "metadata_filter.grade is required and must be a known class id"
        )

    raw_subject = filt.get("subject")
    subject = str(raw_subject).strip() if raw_subject not in (None, "") else ""
    class_subjects = {
        str(row.get("id"))
        for row in (catalog[grade].get("subjects") or [])
        if isinstance(row, dict) and row.get("id")
    }

    if route == "search" and (not subject or subject not in class_subjects):
        raise MadrstyScopeError(
            "metadata_filter.subject is required and must be a subject of the selected grade"
        )

    expected = str(skill_subject or "").strip()
    if route == "answer" and subject and expected and subject != expected:
        raise MadrstyScopeError(
            "metadata_filter.subject conflicts with the selected skill"
        )


def check_project_retrieval_scope(
    project,
    metadata_filter: dict[str, Any] | None,
    *,
    route: RouteName,
    skill_id: str | None = None,
) -> None:
    """Load this pack's class catalog and validate the request filter."""
    domain = _domain_key(project)
    if domain != "madrsty":
        return

    from services.FieldRegistry import get_field_registry
    from services.rag.skills import resolve_skill

    registry = get_field_registry()
    pack = registry.get_pack("madrsty")
    skill_subject = None
    if route == "answer" and skill_id:
        profile = registry.build_profile(
            "madrsty",
            project_overrides=getattr(project, "config_json", None) or {},
        )
        ctx = resolve_skill(profile, skill_id)
        if ctx is not None:
            extra = (ctx.metadata_filters or {}).get("extra") or {}
            raw = extra.get("subject")
            if raw not in (None, ""):
                skill_subject = str(raw).strip()

    validate_madrsty_retrieval_scope(
        domain_key=domain,
        classes=pack.classes,
        metadata_filter=metadata_filter,
        route=route,
        skill_subject=skill_subject,
    )


def check_retrieval_scope(
    project,
    metadata_filter: dict[str, Any] | None = None,
    *,
    route: str,
    skill_id: str | None = None,
) -> str | None:
    """Pack hook used by the shared route. A returned message becomes HTTP 422."""
    try:
        check_project_retrieval_scope(
            project,
            metadata_filter,
            route=route,  # type: ignore[arg-type]
            skill_id=skill_id,
        )
    except MadrstyScopeError as exc:
        return str(exc)
    return None
