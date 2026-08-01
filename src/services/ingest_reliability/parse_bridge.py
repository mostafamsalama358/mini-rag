"""Map Document Intelligence outcomes to ingest ParseOutcomeClass."""

from __future__ import annotations

from typing import Any, Optional

from services.ingest_reliability.models import ParseOutcomeClass


def map_extraction_outcome(
    extraction: Optional[dict[str, Any]],
    *,
    element_count: int = 0,
) -> tuple[ParseOutcomeClass, str]:
    if not extraction:
        if element_count <= 0:
            return ParseOutcomeClass.FAILED, "missing_extraction"
        return ParseOutcomeClass.SUCCESS, "implicit_success"

    outcome = str(extraction.get("outcome") or "").lower()
    reason = str(extraction.get("reason") or "unspecified")

    if outcome in ("full", "success"):
        if element_count <= 0:
            return ParseOutcomeClass.FAILED, "empty_after_success"
        return ParseOutcomeClass.SUCCESS, reason if reason != "unspecified" else "full"
    if outcome == "degraded":
        if element_count <= 0:
            return ParseOutcomeClass.FAILED, reason or "degraded_empty"
        return ParseOutcomeClass.DEGRADED, reason
    if outcome in ("failed", "error"):
        return ParseOutcomeClass.FAILED, reason
    if element_count <= 0:
        return ParseOutcomeClass.FAILED, "unknown_empty"
    return ParseOutcomeClass.DEGRADED, reason or "unknown_outcome"
