"""Shadow dual-run: legacy + unified concurrently; legacy wins for users."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from helpers.config import Settings, get_settings
from models.db_schemes import Project
from services.FieldRegistry import FieldProfile
from services.rag.pipeline.legacy_executor import LegacyPipelineExecutor
from services.rag.pipeline.models import (
    PipelineAnswerResponse,
    PipelineExecutionContext,
    PipelineOutcome,
    ShadowComparisonRecord,
    UnifiedPipelineResult,
)
from services.rag.pipeline.response_adapter import ResponseAdapter
from services.rag.pipeline.shadow_diagnostics import (
    answer_similarity,
    first_divergent_stage,
)
from services.rag.pipeline.shadow_store import ShadowComparisonStore
from utils.metrics import RAG_SHADOW_DIVERGENCE_TOTAL

logger = logging.getLogger("uvicorn.error")


class ShadowRunner:
    """Run legacy and unified in parallel; return legacy; persist comparison."""

    def __init__(
        self,
        *,
        legacy_executor: LegacyPipelineExecutor,
        unified_orchestrator: Any,
        response_adapter: ResponseAdapter | None = None,
        store: ShadowComparisonStore | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._legacy = legacy_executor
        self._unified = unified_orchestrator
        self._adapter = response_adapter or ResponseAdapter()
        self._store = store
        self._settings = settings

    def _cfg(self) -> Settings:
        return self._settings or get_settings()

    async def execute(
        self,
        *,
        project: Project,
        query: str,
        limit: int,
        session_id: str | None,
        metadata_filter: dict[str, Any] | None,
        profile: FieldProfile,
        ctx: PipelineExecutionContext,
    ) -> PipelineAnswerResponse:
        cfg = self._cfg()
        timeout_s = float(cfg.RAG_PIPELINE_UNIFIED_TIMEOUT_S)

        async def _legacy():
            started = time.perf_counter()
            response = await self._legacy.execute(
                project=project,
                query=query,
                limit=limit,
                session_id=session_id,
                metadata_filter=metadata_filter,
                profile=profile,
                ctx=ctx,
            )
            return response, (time.perf_counter() - started) * 1000.0

        async def _unified():
            started = time.perf_counter()
            try:
                result = await asyncio.wait_for(
                    self._unified.execute(
                        project=project,
                        query=query,
                        limit=limit,
                        session_id=session_id,
                        metadata_filter=metadata_filter,
                        profile=profile,
                        ctx=ctx,
                    ),
                    timeout=timeout_s,
                )
                return result, (time.perf_counter() - started) * 1000.0, None
            except asyncio.TimeoutError:
                return None, (time.perf_counter() - started) * 1000.0, "timeout"
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                return None, (time.perf_counter() - started) * 1000.0, f"{type(exc).__name__}: {exc}"

        try:
            legacy_task = asyncio.create_task(_legacy())
            unified_task = asyncio.create_task(_unified())
            legacy_done, unified_done = await asyncio.gather(
                legacy_task, unified_task, return_exceptions=True
            )
        except asyncio.CancelledError:
            raise

        if isinstance(legacy_done, BaseException):
            if isinstance(legacy_done, asyncio.CancelledError):
                raise legacy_done
            raise legacy_done

        legacy_response, legacy_latency_ms = legacy_done
        unified_result: UnifiedPipelineResult | None = None
        unified_latency_ms: float | None = None
        unified_error: str | None = None
        if isinstance(unified_done, BaseException):
            if isinstance(unified_done, asyncio.CancelledError):
                raise unified_done
            unified_error = f"{type(unified_done).__name__}: {unified_done}"
        else:
            unified_result, unified_latency_ms, unified_error = unified_done

        if bool(cfg.RAG_PIPELINE_SHADOW_PERSIST):
            await self._persist_comparison(
                project=project,
                query=query,
                ctx=ctx,
                legacy_response=legacy_response,
                legacy_latency_ms=legacy_latency_ms,
                unified_result=unified_result,
                unified_latency_ms=unified_latency_ms,
                unified_error=unified_error,
            )

        return legacy_response

    async def _persist_comparison(
        self,
        *,
        project: Project,
        query: str,
        ctx: PipelineExecutionContext,
        legacy_response: PipelineAnswerResponse,
        legacy_latency_ms: float,
        unified_result: UnifiedPipelineResult | None,
        unified_latency_ms: float | None,
        unified_error: str | None,
    ) -> None:
        cfg = self._cfg()
        threshold = float(cfg.RAG_PIPELINE_SHADOW_DIVERGENCE_THRESHOLD)
        legacy_outcome: PipelineOutcome = (
            "clarification" if legacy_response.needs_clarification else "success"
        )
        if not legacy_response.answer and not legacy_response.needs_clarification:
            legacy_outcome = "no_context"

        unified_outcome: PipelineOutcome = "error"
        unified_answer: str | None = None
        unified_plan_id: str | None = None
        unified_citation_count = 0
        if unified_error == "timeout":
            unified_outcome = "timeout"
        elif unified_result is not None:
            unified_outcome = unified_result.outcome
            adapted = self._adapter.from_unified_result(
                unified_result, original_query=query
            )
            unified_answer = adapted.answer
            unified_plan_id = getattr(
                getattr(unified_result, "retrieval_plan", None), "plan_id", None
            )
            answer_result = unified_result.answer_result
            if answer_result is not None:
                citations = getattr(answer_result, "citations", None) or []
                unified_citation_count = len(citations)
        elif unified_error:
            unified_outcome = "error"

        sim = answer_similarity(legacy_response.answer, unified_answer)
        diverged = (legacy_outcome != unified_outcome) or (sim < threshold)
        stage = first_divergent_stage(
            legacy_outcome=legacy_outcome,
            unified_outcome=unified_outcome,
            retrieval_overlap_score=None,
            evidence_overlap_score=None,
            answer_sim=sim,
            divergence_threshold=threshold,
        )
        record = ShadowComparisonRecord(
            request_id=ctx.request_id,
            project_id=int(project.project_id),
            recorded_at=datetime.now(timezone.utc).isoformat(),
            query_text=query,
            legacy_outcome=legacy_outcome,
            unified_outcome=unified_outcome,
            legacy_answer=legacy_response.answer,
            unified_answer=unified_answer,
            answer_similarity=sim,
            diverged=diverged,
            legacy_latency_ms=legacy_latency_ms,
            unified_latency_ms=unified_latency_ms,
            unified_plan_id=unified_plan_id,
            legacy_citation_count=0,
            unified_citation_count=unified_citation_count,
            unified_error=unified_error,
            first_divergent_stage=stage,
        )
        if diverged:
            RAG_SHADOW_DIVERGENCE_TOTAL.labels(project_id=str(project.project_id)).inc()
        store = self._store
        if store is None:
            store = ShadowComparisonStore(cfg.RAG_PIPELINE_SHADOW_DIR)
        try:
            await store.save(record)
        except Exception:
            logger.exception("shadow_persist_failed request_id=%s", ctx.request_id)
