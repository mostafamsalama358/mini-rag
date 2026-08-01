"""SkillFilterProfile → retrieval metadata_filter merge shape (021)."""

from __future__ import annotations

from typing import Any

from fields.schemas import SkillFilterProfile


def effective_filters(profile: SkillFilterProfile) -> dict[str, Any]:
    """Normalize profile filters for metadata_filter merge.

    ``field`` / ``source`` are SkillFilterProfile retrieval constraints — they are
    consumed as ``field_key`` / soft source hints, NOT as raw JSONB containment
    keys (``metadata @> {"field": [...], "source": [...]}`` matches nothing on
    the live Excel-workbook txt corpus — use ``field_key`` / ``field_name``).


    Absent ``fallback`` on the profile means no silent broaden — callers must
    not widen constraints when retrieval returns empty.
    """
    result: dict[str, Any] = {}
    filters = profile.filters

    if filters.field:
        result["field"] = list(filters.field)
    if filters.source:
        result["source"] = list(filters.source)
    if filters.extra:
        result["extra"] = dict(filters.extra)

    return result


def jsonb_metadata_filter(metadata_filter: dict[str, Any] | None) -> dict[str, Any] | None:
    """Strip Skill profile keys that must not be applied as JSONB ``@>`` filters."""
    if not metadata_filter:
        return None
    cleaned = {
        key: value
        for key, value in metadata_filter.items()
        if key not in {"field", "source", "extra"} and value not in (None, "", [], {})
    }
    extra = metadata_filter.get("extra")
    if isinstance(extra, dict):
        for key, value in extra.items():
            if value not in (None, "", [], {}):
                cleaned[key] = value
    return cleaned or None


def logical_field_key(metadata_filter: dict[str, Any] | None) -> str | None:
    """First Skill profile field name for field-presence search."""
    if not metadata_filter:
        return None
    fields = metadata_filter.get("field")
    if isinstance(fields, list) and fields:
        text = str(fields[0] or "").strip()
        return text or None
    if isinstance(fields, str) and fields.strip():
        return fields.strip()
    return None
