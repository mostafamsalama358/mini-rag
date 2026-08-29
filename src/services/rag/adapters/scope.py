"""Scoped retrieval miss reasons and degrade policy (answer-path honesty)."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from helpers.config import get_settings

logger = logging.getLogger("uvicorn.error")


class ScopeMissReason(str, Enum):
    METADATA_MISSING = "METADATA_MISSING"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    ZERO_MATCHING_CHUNKS = "ZERO_MATCHING_CHUNKS"
    SCOPE_NOT_REQUESTED = "SCOPE_NOT_REQUESTED"
    COLLECTION_MISSING = "COLLECTION_MISSING"


def allow_unscoped_degrade() -> bool:
    return bool(getattr(get_settings(), "RAG_ALLOW_UNSCOPED_DEGRADE", False))


def field_soft_miss_eligible(scope: dict[str, Any]) -> bool:
    """Retry without field_key when a hard field constraint zeros the set.

    Pharmacy uses entity_prefix; Domain Pack extra.* (e.g. extra.subject) is
    carried on metadata_filter. Either is enough to keep the remaining scope.
    """
    if not scope.get("field_key"):
        return False
    return bool(
        scope.get("entity_prefix")
        or scope.get("entity_prefixes")
        or scope.get("metadata_filter")
    )


def resolve_entity_prefixes(scope: dict[str, Any]) -> list[str]:
    """Deduped entity prefixes from scope (multi-entity compare aware)."""
    out: list[str] = []
    for raw in list(scope.get("entity_prefixes") or []) + (
        [scope.get("entity_prefix")] if scope.get("entity_prefix") else []
    ):
        text = str(raw or "").strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= 8:
            break
    return out


def per_entity_fetch_limit(total_limit: int, entity_count: int) -> int:
    """Quota per brand so compare queries are not starved by one entity."""
    n = max(1, int(entity_count))
    total = max(1, int(total_limit))
    return max(3, (total + n - 1) // n)


def merge_retrieved_docs(docs_lists: list[list[Any]], *, limit: int) -> list[Any]:
    """Merge per-entity result lists; prefer higher scores; dedupe by text."""
    merged: list[Any] = []
    seen: set[str] = set()
    for docs in docs_lists:
        for doc in docs or []:
            text = (getattr(doc, "text", None) or "")[:240]
            key = text.casefold()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(doc)
    merged.sort(
        key=lambda d: float(getattr(d, "score", 0.0) or 0.0),
        reverse=True,
    )
    return merged[: max(1, int(limit))]


def classify_scoped_miss(scope: dict[str, Any]) -> ScopeMissReason:
    """Classify empty scoped results using the *request* scope (not row stats)."""
    entity_key = scope.get("entity_key")
    entity_prefix = scope.get("entity_prefix")
    entity_prefixes = scope.get("entity_prefixes") or []
    has_entity = bool(entity_prefix) or bool(entity_prefixes)
    field_key = scope.get("field_key")
    # Request asked for entity scope but index/manifest never supplied a key.
    if has_entity and not entity_key:
        return ScopeMissReason.METADATA_MISSING
    if field_key or (entity_key and has_entity) or scope.get("metadata_filter"):
        # Distinguishing ENTITY_NOT_FOUND vs ZERO_MATCH needs index probes;
        # default to ZERO_MATCHING_CHUNKS when a complete scope was applied.
        if has_entity and entity_key:
            return ScopeMissReason.ENTITY_NOT_FOUND
        return ScopeMissReason.ZERO_MATCHING_CHUNKS
    return ScopeMissReason.SCOPE_NOT_REQUESTED


def log_scoped_miss(
    *,
    channel: str,
    collection_name: str,
    scope: dict[str, Any],
    reason: ScopeMissReason,
    degraded: bool,
) -> None:
    prefixes = scope.get("entity_prefixes") or (
        [scope.get("entity_prefix")] if scope.get("entity_prefix") else []
    )
    logger.info(
        "%s_scoped_miss collection=%s reason=%s degraded=%s entity_key=%r "
        "entity_prefix=%r entity_prefixes=%r field_key=%r",
        channel,
        collection_name,
        reason.value,
        degraded,
        scope.get("entity_key"),
        scope.get("entity_prefix"),
        prefixes,
        scope.get("field_key"),
    )


def apply_field_score_boost(
    docs: list[Any],
    *,
    field_key: str | None,
    boost: float = 0.15,
    penalty: float = 0.08,
) -> list[Any]:
    """Re-score RetrievedDocument-like rows for field/section fidelity."""
    if not field_key or not docs:
        return docs

    target = str(field_key).strip().lower()
    if not target or target in {"unknown", "product_name"}:
        return docs

    related_penalty_fields = {
        "contraindications": {"interactions", "warnings"},
        "interactions": {"contraindications"},
        "pregnancy": {"interactions", "side_effects"},
        "side_effects": {"interactions"},
        "dosage": {"storage", "ingredients"},
    }
    penalize = related_penalty_fields.get(target, set())

    rescored: list[tuple[float, Any]] = []
    for doc in docs:
        meta = getattr(doc, "metadata", None) or {}
        base = float(getattr(doc, "score", 0.0) or 0.0)
        field_name = str(meta.get("field_name") or "").strip().lower()
        field_names = meta.get("field_names") or []
        if isinstance(field_names, str):
            field_names = [field_names]
        names = {str(x).strip().lower() for x in field_names if x}
        section = str(meta.get("section") or meta.get("heading_path") or "").lower()
        text = (getattr(doc, "text", None) or "").lower()

        delta = 0.0
        if field_name == target or target in names:
            delta += boost
        elif field_name in penalize or names.intersection(penalize):
            delta -= penalty
        # Soft lexical section preference when metadata incomplete.
        if target.replace("_", " ") in section or target.replace("_", " ") in text[:240]:
            delta += boost * 0.5

        new_score = base + delta
        try:
            doc.score = new_score
        except Exception:
            pass
        rescored.append((new_score, doc))

    rescored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in rescored]
