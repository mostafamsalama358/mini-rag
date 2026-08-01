"""Pipeline mode resolution for migration feature flags (spec 015)."""

from __future__ import annotations

from typing import Any

from helpers.config import Settings, get_settings
from services.rag.pipeline.models import PipelineMode

_VALID_MODES: frozenset[str] = frozenset({"legacy", "shadow", "unified"})


def _parse_canary_ids(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {part.strip() for part in str(raw).split(",") if part.strip()}


class PipelineModeResolver:
    """Resolve effective PipelineMode per contracts/orchestrator.md."""

    def resolve(
        self,
        *,
        project_id: int,
        project_config: dict[str, Any] | None = None,
        settings: Settings | None = None,
    ) -> PipelineMode:
        cfg = settings or get_settings()

        # 1. Per-project override
        if project_config:
            raw = project_config.get("pipeline_mode")
            if isinstance(raw, str) and raw.strip().lower() in _VALID_MODES:
                return raw.strip().lower()  # type: ignore[return-value]

        # 2. Canary allowlist forces unified
        canary = _parse_canary_ids(getattr(cfg, "RAG_PIPELINE_CANARY_PROJECT_IDS", ""))
        if str(project_id) in canary:
            return "unified"

        # 3. Global settings default
        mode = str(getattr(cfg, "RAG_PIPELINE_MODE", "legacy") or "legacy").strip().lower()
        if mode in _VALID_MODES:
            return mode  # type: ignore[return-value]
        return "legacy"
