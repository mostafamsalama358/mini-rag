"""Operational history append helpers (no secrets)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

_SECRET_KEY_FRAGMENTS = (
    "password",
    "secret",
    "api_key",
    "apikey",
    "token",
    "authorization",
    "credential",
)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, inner in value.items():
            key_l = str(key).lower()
            if any(frag in key_l for frag in _SECRET_KEY_FRAGMENTS):
                out[str(key)] = "[REDACTED]"
            else:
                out[str(key)] = _redact(inner)
        return out
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def build_history_event(
    *,
    job_id: str,
    correlation_id: str,
    event_type: str,
    detail: dict[str, Any],
    stage: Optional[str] = None,
) -> dict[str, Any]:
    """Build a sanitized operational history event dict (persistable)."""
    return {
        "event_id": str(uuid4()),
        "job_id": job_id,
        "correlation_id": correlation_id,
        "event_type": event_type,
        "stage": stage,
        "detail": _redact(detail or {}),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def append_event(
    history: list[dict[str, Any]],
    *,
    job_id: str,
    correlation_id: str,
    event_type: str,
    detail: dict[str, Any],
    stage: Optional[str] = None,
) -> dict[str, Any]:
    """Append a sanitized event to an in-memory history list and return it."""
    event = build_history_event(
        job_id=job_id,
        correlation_id=correlation_id,
        event_type=event_type,
        detail=detail,
        stage=stage,
    )
    history.append(event)
    return event
