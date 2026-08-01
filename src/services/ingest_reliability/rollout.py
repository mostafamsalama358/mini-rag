"""Canary / cohort rollout resolution."""

from __future__ import annotations

from helpers.config import Settings


def parse_canary_project_ids(settings: Settings) -> set[int]:
    raw = (settings.INGEST_CANARY_PROJECT_IDS or "").strip()
    if not raw:
        return set()
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def scalable_path_enabled_for_project(project_id: int, settings: Settings) -> bool:
    if not settings.INGEST_RELIABILITY_ENABLED:
        return False
    canaries = parse_canary_project_ids(settings)
    if not canaries:
        return True  # empty allowlist = all projects when feature enabled
    return project_id in canaries
