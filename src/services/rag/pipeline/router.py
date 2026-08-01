"""PipelineRouter — single injection point for /answer mode selection."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Protocol

from helpers.config import Settings, get_settings
from models.db_schemes import Project
from services.FieldRegistry import FieldProfile
from services.rag.pipeline.context import build_execution_context
from services.rag.pipeline.legacy_executor import LegacyPipelineExecutor
from services.rag.pipeline.mode_resolver import PipelineModeResolver
from services.rag.pipeline.models import PipelineAnswerResponse, PipelineMode
from services.rag.pipeline.response_adapter import ResponseAdapter
from services.rag.pipeline.skill_orchestrator import profile_has_skills
from services.rag.pipeline.telemetry import log_pipeline_complete
from utils.detect_language import detect_query_language
from utils.metrics import PIPELINE_FALLBACK_TOTAL, RAG_PIPELINE_REQUESTS_TOTAL

logger = logging.getLogger("uvicorn.error")


class _UnifiedOrchestrator(Protocol):
    async def execute(self, **kwargs: Any) -> Any: ...


class _ShadowRunner(Protocol):
    async def execute(self, **kwargs: Any) -> PipelineAnswerResponse: ...


class _SkillRuntime(Protocol):
    async def execute(self, **kwargs: Any) -> PipelineAnswerResponse: ...


class PipelineRouter:
    """Route /answer traffic to legacy, unified, or shadow executors."""

    def __init__(
        self,
        *,
        legacy_executor: LegacyPipelineExecutor,
        unified_orchestrator: _UnifiedOrchestrator | None = None,
        shadow_runner: _ShadowRunner | None = None,
        skill_runtime: _SkillRuntime | None = None,
        mode_resolver: PipelineModeResolver | None = None,
        response_adapter: ResponseAdapter | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._legacy = legacy_executor
        self._unified = unified_orchestrator
        self._shadow = shadow_runner
        self._skill_runtime = skill_runtime
        self._resolver = mode_resolver or PipelineModeResolver()
        self._adapter = response_adapter or ResponseAdapter()
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
        skill_id: str | None = None,
    ) -> PipelineAnswerResponse:
        cfg = self._cfg()
        project_config = getattr(project, "config_json", None) or {}
        mode: PipelineMode = self._resolver.resolve(
            project_id=int(project.project_id),
            project_config=project_config if isinstance(project_config, dict) else None,
            settings=cfg,
        )
        locale = detect_query_language(query, default="en")
        ctx = build_execution_context(
            project_id=int(project.project_id),
            profile=profile,
            limit=limit,
            mode=mode,
            session_id=session_id,
            metadata_filter=metadata_filter,
            locale=locale,
            project_config=project_config if isinstance(project_config, dict) else None,
            settings=cfg,
            skill_id=skill_id,
        )
        logger.info(
            "rag_pipeline_mode_resolved request_id=%s project_id=%s mode=%s",
            ctx.request_id,
            ctx.project_id,
            mode,
        )

        started = time.perf_counter()
        if profile_has_skills(profile):
            if self._skill_runtime is None:
                raise RuntimeError("Skill runtime orchestrator not configured")
            response = await self._skill_runtime.execute(
                project=project,
                query=query,
                limit=limit,
                session_id=session_id,
                metadata_filter=metadata_filter,
                profile=profile,
                ctx=ctx,
                skill_id=skill_id,
            )
            outcome = "clarification" if response.needs_clarification else "success"
            if not response.answer and not response.needs_clarification:
                outcome = "no_context"
            RAG_PIPELINE_REQUESTS_TOTAL.labels(mode=str(mode), outcome=outcome).inc()
            log_pipeline_complete(
                request_id=ctx.request_id,
                project_id=ctx.project_id,
                mode=str(mode),
                outcome=outcome,
                duration_ms=(time.perf_counter() - started) * 1000.0,
            )
            return response

        if mode == "shadow":
            if self._shadow is None:
                raise RuntimeError("Shadow runner not configured")
            response = await self._shadow.execute(
                project=project,
                query=query,
                limit=limit,
                session_id=session_id,
                metadata_filter=metadata_filter,
                profile=profile,
                ctx=ctx,
            )
            outcome = "clarification" if response.needs_clarification else "success"
            RAG_PIPELINE_REQUESTS_TOTAL.labels(mode="shadow", outcome=outcome).inc()
            log_pipeline_complete(
                request_id=ctx.request_id,
                project_id=ctx.project_id,
                mode="shadow",
                outcome=outcome,
                duration_ms=(time.perf_counter() - started) * 1000.0,
            )
            return response

        if mode == "unified":
            return await self._execute_unified(
                project=project,
                query=query,
                limit=limit,
                session_id=session_id,
                metadata_filter=metadata_filter,
                profile=profile,
                ctx=ctx,
                started=started,
                skill_id=skill_id,
            )

        response = await self._legacy.execute(
            project=project,
            query=query,
            limit=limit,
            session_id=session_id,
            metadata_filter=metadata_filter,
            profile=profile,
            ctx=ctx,
            skill_id=skill_id,
        )
        outcome = "clarification" if response.needs_clarification else "success"
        if not response.answer and not response.needs_clarification:
            outcome = "no_context"
        RAG_PIPELINE_REQUESTS_TOTAL.labels(mode="legacy", outcome=outcome).inc()
        log_pipeline_complete(
            request_id=ctx.request_id,
            project_id=ctx.project_id,
            mode="legacy",
            outcome=outcome,
            duration_ms=(time.perf_counter() - started) * 1000.0,
        )
        return response

    async def _execute_unified(
        self,
        *,
        project: Project,
        query: str,
        limit: int,
        session_id: str | None,
        metadata_filter: dict[str, Any] | None,
        profile: FieldProfile,
        ctx: Any,
        started: float,
        skill_id: str | None = None,
    ) -> PipelineAnswerResponse:
        if self._unified is None:
            raise RuntimeError("Unified orchestrator not configured")

        cfg = self._cfg()
        try:
            result = await self._unified.execute(
                project=project,
                query=query,
                limit=limit,
                session_id=session_id,
                metadata_filter=metadata_filter,
                profile=profile,
                ctx=ctx,
            )
            response = self._adapter.from_unified_result(result, original_query=query)
            outcome = getattr(result, "outcome", "success")
            RAG_PIPELINE_REQUESTS_TOTAL.labels(mode="unified", outcome=str(outcome)).inc()
            log_pipeline_complete(
                request_id=ctx.request_id,
                project_id=ctx.project_id,
                mode="unified",
                outcome=str(outcome),
                duration_ms=(time.perf_counter() - started) * 1000.0,
                plan_id=getattr(getattr(result, "retrieval_plan", None), "plan_id", None),
                context_id=getattr(getattr(result, "built_context", None), "context_id", None),
            )
            if outcome in ("error", "timeout") and bool(cfg.RAG_PIPELINE_FALLBACK_ON_ERROR):
                PIPELINE_FALLBACK_TOTAL.labels(reason=str(outcome)).inc()
                return await self._legacy.execute(
                    project=project,
                    query=query,
                    limit=limit,
                    session_id=session_id,
                    metadata_filter=metadata_filter,
                    profile=profile,
                    ctx=ctx,
                    skill_id=skill_id,
                )
            return response
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception(
                "unified_pipeline_error request_id=%s project_id=%s err=%s",
                ctx.request_id,
                ctx.project_id,
                exc,
            )
            RAG_PIPELINE_REQUESTS_TOTAL.labels(mode="unified", outcome="error").inc()
            if bool(cfg.RAG_PIPELINE_FALLBACK_ON_ERROR):
                PIPELINE_FALLBACK_TOTAL.labels(reason=type(exc).__name__).inc()
                return await self._legacy.execute(
                    project=project,
                    query=query,
                    limit=limit,
                    session_id=session_id,
                    metadata_filter=metadata_filter,
                    profile=profile,
                    ctx=ctx,
                    skill_id=skill_id,
                )
            raise
