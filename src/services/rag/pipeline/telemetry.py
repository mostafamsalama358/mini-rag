"""Structured logging helpers for pipeline stage traces."""

from __future__ import annotations

import logging
import time
from typing import Any

from services.rag.pipeline.models import (
    PipelineStageTrace,
    StageName,
    StageStatus,
)
from utils.metrics import RAG_PIPELINE_STAGE_DURATION

logger = logging.getLogger("uvicorn.error")


def append_stage_trace(
    traces: list[PipelineStageTrace],
    *,
    stage: StageName,
    status: StageStatus,
    started_at: float,
    plan_id: str | None = None,
    context_id: str | None = None,
    error_type: str | None = None,
    detail: dict[str, Any] | None = None,
) -> PipelineStageTrace:
    duration_ms = (time.perf_counter() - started_at) * 1000.0
    trace = PipelineStageTrace(
        stage=stage,
        status=status,
        started_at=started_at,
        duration_ms=duration_ms,
        outcome=status,
        plan_id=plan_id,
        context_id=context_id,
        error_type=error_type,
        detail=detail,
    )
    traces.append(trace)
    try:
        RAG_PIPELINE_STAGE_DURATION.labels(stage=stage, status=status).observe(
            duration_ms / 1000.0
        )
    except Exception:
        pass
    return trace


def log_pipeline_complete(
    *,
    request_id: str,
    project_id: int,
    mode: str,
    outcome: str,
    duration_ms: float,
    plan_id: str | None = None,
    context_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": "rag_pipeline_complete",
        "request_id": request_id,
        "project_id": project_id,
        "mode": mode,
        "outcome": outcome,
        "duration_ms": round(duration_ms, 3),
        "plan_id": plan_id,
        "context_id": context_id,
    }
    if extra:
        payload.update(extra)
    logger.info("%s", payload)
