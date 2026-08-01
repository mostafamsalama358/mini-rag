"""Validated configuration version helpers."""

from __future__ import annotations

from helpers.config import Settings


def validate_ingest_config(settings: Settings) -> tuple[bool, str]:
    if settings.INGEST_MAX_CONCURRENT_JOBS < 1:
        return False, "INGEST_MAX_CONCURRENT_JOBS must be >= 1"
    if settings.INGEST_MAX_BACKLOG < 0:
        return False, "INGEST_MAX_BACKLOG must be >= 0"
    if settings.INGEST_STALL_SECONDS < 1:
        return False, "INGEST_STALL_SECONDS must be >= 1"
    if settings.INGEST_POISON_THRESHOLD < 1:
        return False, "INGEST_POISON_THRESHOLD must be >= 1"
    if not (settings.INGEST_CONFIG_VERSION or "").strip():
        return False, "INGEST_CONFIG_VERSION required"
    return True, "ok"


def config_version_or_raise(settings: Settings) -> str:
    ok, reason = validate_ingest_config(settings)
    if not ok:
        raise ValueError(reason)
    return settings.INGEST_CONFIG_VERSION
