"""Integration tests for legacy pipeline path parity."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from models.enums.ResponseEnums import ResponseSignal
from services.rag.pipeline.legacy_executor import LegacyPipelineExecutor
from services.rag.pipeline.models import PipelineExecutionContext, PipelineSettingsSnapshot
from services.rag.pipeline.response_adapter import ResponseAdapter
from services.rag.pipeline.router import PipelineRouter


def _ctx(**overrides):
    base = dict(
        request_id="req-1",
        project_id=1,
        session_id=None,
        mode="legacy",
        profile=SimpleNamespace(domain_key="pharmacy"),
        metadata_filter=None,
        limit=8,
        locale="en",
        started_at=0.0,
        deadline_at=45.0,
        pipeline_version="1.0.0",
        settings_snapshot=PipelineSettingsSnapshot(
            pipeline_mode="legacy",
            fallback_on_error=True,
            unified_timeout_s=45.0,
            hybrid_search_enabled=True,
            reranker_enabled=True,
            semantic_parser_enabled=True,
        ),
    )
    base.update(overrides)
    return PipelineExecutionContext(**base)


@pytest.mark.asyncio
async def test_legacy_executor_preserves_tuple_mapping():
    rag = MagicMock()
    rag.answer_question = AsyncMock(return_value=("answer text", "full", [{"r": 1}], False))
    executor = LegacyPipelineExecutor(rag_service=rag, response_adapter=ResponseAdapter())
    project = SimpleNamespace(project_id=1, config_json={})
    profile = SimpleNamespace(domain_key="pharmacy")
    resp = await executor.execute(
        project=project,
        query="dose?",
        limit=8,
        session_id=None,
        metadata_filter=None,
        profile=profile,
        ctx=_ctx(),
    )
    assert resp.answer == "answer text"
    assert resp.full_prompt == "full"
    assert resp.needs_clarification is False
    assert resp.signal == ResponseSignal.RAG_ANSWER_SUCCESS


@pytest.mark.asyncio
async def test_router_legacy_mode_delegates_to_executor():
    rag = MagicMock()
    rag.answer_question = AsyncMock(return_value=("ok", None, None, False))
    settings = SimpleNamespace(
        RAG_PIPELINE_MODE="legacy",
        RAG_PIPELINE_FALLBACK_ON_ERROR=True,
        RAG_PIPELINE_UNIFIED_TIMEOUT_S=45.0,
        RAG_PIPELINE_SHADOW_DIVERGENCE_THRESHOLD=0.85,
        RAG_PIPELINE_CANARY_PROJECT_IDS="",
        RAG_ENABLE_HYBRID_SEARCH=True,
        RAG_ENABLE_RERANKER=True,
        RAG_SEMANTIC_PARSER_ENABLED=True,
    )
    router = PipelineRouter(
        legacy_executor=LegacyPipelineExecutor(rag_service=rag),
        settings=settings,
    )
    project = SimpleNamespace(project_id=9, config_json={})
    profile = SimpleNamespace(domain_key="pharmacy")
    resp = await router.execute(
        project=project,
        query="what is the dose",
        limit=5,
        session_id=None,
        metadata_filter=None,
        profile=profile,
    )
    assert resp.answer == "ok"
    rag.answer_question.assert_awaited_once()
