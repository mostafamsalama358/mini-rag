"""Immutable execution-context builder for pipeline requests."""

from __future__ import annotations

import time
import uuid
from typing import Any

from helpers.config import Settings, get_settings
from services.rag.pipeline import PIPELINE_VERSION
from services.rag.pipeline.models import (
    PipelineExecutionContext,
    PipelineMode,
    PipelineSettingsSnapshot,
)
from services.rag.pipeline.mode_resolver import PipelineModeResolver


def build_settings_snapshot(
    *,
    mode: PipelineMode,
    settings: Settings | None = None,
) -> PipelineSettingsSnapshot:
    cfg = settings or get_settings()
    timeout = float(cfg.RAG_PIPELINE_UNIFIED_TIMEOUT_S)
    if timeout <= 0:
        raise ValueError("RAG_PIPELINE_UNIFIED_TIMEOUT_S must be > 0")
    threshold = float(cfg.RAG_PIPELINE_SHADOW_DIVERGENCE_THRESHOLD)
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("RAG_PIPELINE_SHADOW_DIVERGENCE_THRESHOLD must be in [0.0, 1.0]")
    return PipelineSettingsSnapshot(
        pipeline_mode=mode,
        fallback_on_error=bool(cfg.RAG_PIPELINE_FALLBACK_ON_ERROR),
        unified_timeout_s=timeout,
        hybrid_search_enabled=bool(cfg.RAG_ENABLE_HYBRID_SEARCH),
        reranker_enabled=bool(cfg.RAG_ENABLE_RERANKER),
        semantic_parser_enabled=bool(cfg.RAG_SEMANTIC_PARSER_ENABLED),
    )


def build_execution_context(
    *,
    project_id: int,
    profile: Any,
    limit: int,
    mode: PipelineMode | None = None,
    session_id: str | None = None,
    metadata_filter: dict[str, Any] | None = None,
    locale: str = "en",
    request_id: str | None = None,
    project_config: dict[str, Any] | None = None,
    settings: Settings | None = None,
    started_at: float | None = None,
    skill_id: str | None = None,
    skill_ctx: Any | None = None,
) -> PipelineExecutionContext:
    """Create a frozen PipelineExecutionContext at router entry."""
    cfg = settings or get_settings()
    resolved_mode = mode or PipelineModeResolver().resolve(
        project_id=project_id,
        project_config=project_config,
        settings=cfg,
    )
    start = started_at if started_at is not None else time.perf_counter()
    snapshot = build_settings_snapshot(mode=resolved_mode, settings=cfg)
    return PipelineExecutionContext(
        request_id=request_id or str(uuid.uuid4()),
        project_id=int(project_id),
        session_id=session_id,
        mode=resolved_mode,
        profile=profile,
        metadata_filter=metadata_filter,
        limit=int(limit),
        locale=locale or "en",
        started_at=start,
        deadline_at=start + snapshot.unified_timeout_s,
        pipeline_version=PIPELINE_VERSION,
        settings_snapshot=snapshot,
        skill_id=skill_id,
        skill_ctx=skill_ctx,
    )
