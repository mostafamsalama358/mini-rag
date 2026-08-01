"""Failure classification: transient vs permanent + ownership."""

from __future__ import annotations

from dataclasses import dataclass

from services.ingest_reliability.models import FailureOwnership


@dataclass(frozen=True)
class FailureClass:
    kind: str  # transient | permanent
    ownership: FailureOwnership
    reason: str


_TRANSIENT_HINTS = (
    "timeout",
    "unavailable",
    "connection",
    "temporarily",
    "rate limit",
    "429",
    "503",
)


def classify_failure(exc: BaseException | str, *, ownership_hint: FailureOwnership | None = None) -> FailureClass:
    text = str(exc).lower()
    if ownership_hint is None:
        if "unauthorized" in text or "forbidden" in text or "policy" in text:
            ownership = FailureOwnership.USER_INPUT
        elif "corrupt" in text or "unreadable" in text or "parse" in text:
            ownership = FailureOwnership.DOCUMENT_QUALITY
        elif any(h in text for h in ("embedding", "storage", "database", "ocr", "llm")):
            ownership = FailureOwnership.EXTERNAL_DEPENDENCY
        elif "cancel" in text:
            ownership = FailureOwnership.OPERATOR_ACTION
        else:
            ownership = FailureOwnership.PLATFORM
    else:
        ownership = ownership_hint

    if ownership in (FailureOwnership.USER_INPUT, FailureOwnership.DOCUMENT_QUALITY, FailureOwnership.OPERATOR_ACTION):
        return FailureClass("permanent", ownership, text[:200])
    if any(h in text for h in _TRANSIENT_HINTS):
        return FailureClass("transient", ownership, text[:200])
    if ownership == FailureOwnership.EXTERNAL_DEPENDENCY:
        return FailureClass("transient", ownership, text[:200])
    return FailureClass("permanent", ownership, text[:200])


def should_retry(failure: FailureClass, attempt: int, max_retries: int) -> bool:
    return failure.kind == "transient" and attempt < max_retries
