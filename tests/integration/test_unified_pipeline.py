"""Integration test stubs for unified / fallback / parser parity / golden / startup."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.rag.pipeline.legacy_executor import LegacyPipelineExecutor
from services.rag.pipeline.models import UnifiedPipelineResult
from services.rag.pipeline.router import PipelineRouter
from services.rag.pipeline.snapshot_builder import build_pipeline_snapshot


class _ExplodingUnified:
    async def execute(self, **kwargs):
        raise RuntimeError("boom")


class _TraceUnified:
    async def execute(self, **kwargs):
        ctx = kwargs["ctx"]
        from services.rag.pipeline.models import PipelineStageTrace

        traces = [
            PipelineStageTrace(stage=s, status="completed", started_at=0.0, duration_ms=1.0)
            for s in ("parse", "plan", "retrieve", "evidence", "context", "answer")
        ]
        return UnifiedPipelineResult(
            execution_context=ctx,
            outcome="success",
            stage_traces=traces,
            answer_result=SimpleNamespace(
                answer="unified-ok", citations=[], no_answer=False
            ),
        )


def _settings(mode="unified", **overrides):
    base = dict(
        RAG_PIPELINE_MODE=mode,
        RAG_PIPELINE_FALLBACK_ON_ERROR=True,
        RAG_PIPELINE_SHADOW_PERSIST=False,
        RAG_PIPELINE_SHADOW_DIR=".rag_shadow/",
        RAG_PIPELINE_UNIFIED_TIMEOUT_S=45.0,
        RAG_PIPELINE_SHADOW_DIVERGENCE_THRESHOLD=0.85,
        RAG_PIPELINE_CANARY_PROJECT_IDS="",
        RAG_ENABLE_HYBRID_SEARCH=True,
        RAG_ENABLE_RERANKER=True,
        RAG_SEMANTIC_PARSER_ENABLED=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_unified_pipeline_stage_wiring():
    router = PipelineRouter(
        legacy_executor=LegacyPipelineExecutor(rag_service=MagicMock()),
        unified_orchestrator=_TraceUnified(),
        settings=_settings("unified", RAG_PIPELINE_FALLBACK_ON_ERROR=False),
    )
    resp = await router.execute(
        project=SimpleNamespace(project_id=1, config_json={}),
        query="q",
        limit=5,
        session_id=None,
        metadata_filter=None,
        profile=SimpleNamespace(domain_key="pharmacy"),
    )
    assert resp.answer == "unified-ok"


@pytest.mark.asyncio
async def test_pipeline_fallback_on_unified_error():
    rag = MagicMock()
    rag.answer_question = AsyncMock(return_value=("legacy-fallback", None, None, False))
    router = PipelineRouter(
        legacy_executor=LegacyPipelineExecutor(rag_service=rag),
        unified_orchestrator=_ExplodingUnified(),
        settings=_settings("unified", RAG_PIPELINE_FALLBACK_ON_ERROR=True),
    )
    resp = await router.execute(
        project=SimpleNamespace(project_id=1, config_json={}),
        query="q",
        limit=5,
        session_id=None,
        metadata_filter=None,
        profile=SimpleNamespace(domain_key="pharmacy"),
    )
    assert resp.answer == "legacy-fallback"
    rag.answer_question.assert_awaited()


def test_parser_parity_hash_placeholder():
    # Structural placeholder — shared QueryParseService is the single parse path.
    from services.rag.pipeline import query_parse_service as qps

    assert hasattr(qps, "QueryParseService")


def test_snapshot_builder_for_golden():
    from services.rag.pipeline.models import (
        PipelineExecutionContext,
        PipelineSettingsSnapshot,
        PipelineStageTrace,
    )

    ctx = PipelineExecutionContext(
        request_id="r1",
        project_id=1,
        mode="unified",
        profile=SimpleNamespace(),
        limit=8,
        locale="en",
        started_at=0.0,
        deadline_at=1.0,
        pipeline_version="1.0.0",
        settings_snapshot=PipelineSettingsSnapshot(
            pipeline_mode="unified",
            fallback_on_error=True,
            unified_timeout_s=45.0,
            hybrid_search_enabled=True,
            reranker_enabled=True,
            semantic_parser_enabled=True,
        ),
    )
    result = UnifiedPipelineResult(
        execution_context=ctx,
        outcome="success",
        stage_traces=[
            PipelineStageTrace(stage="parse", status="completed", started_at=0.0, duration_ms=1.0)
        ],
        answer_result=SimpleNamespace(answer="a", citations=[], no_answer=False),
    )
    snap = build_pipeline_snapshot(result)
    assert snap["outcome"] == "success"
    assert snap["answer"] == "a"


def test_startup_fail_fast_missing_clients(monkeypatch):
    from services.rag.composition import build_rag_pipeline_factory

    monkeypatch.setenv("RAG_PIPELINE_MODE", "unified")
    # Bypass Settings load; force shadow/unified validation path.
    fake = SimpleNamespace(
        RAG_PIPELINE_MODE="unified",
        RAG_RRF_K=60,
        RAG_ENABLE_RERANKER=False,
    )
    monkeypatch.setattr("services.rag.composition.get_settings", lambda: fake)
    with pytest.raises(RuntimeError, match="vectordb_client"):
        build_rag_pipeline_factory(SimpleNamespace())
