"""Integration tests for pipeline mode rollback / canary resolution."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.rag.pipeline.legacy_executor import LegacyPipelineExecutor
from services.rag.pipeline.mode_resolver import PipelineModeResolver
from services.rag.pipeline.router import PipelineRouter


def test_flag_flip_to_legacy_resolves_next_request():
    resolver = PipelineModeResolver()
    settings = SimpleNamespace(
        RAG_PIPELINE_MODE="unified",
        RAG_PIPELINE_CANARY_PROJECT_IDS="",
    )
    assert resolver.resolve(project_id=1, settings=settings) == "unified"
    settings.RAG_PIPELINE_MODE = "legacy"
    assert resolver.resolve(project_id=1, settings=settings) == "legacy"


def test_project_override_rollback_without_env_change():
    resolver = PipelineModeResolver()
    settings = SimpleNamespace(
        RAG_PIPELINE_MODE="unified",
        RAG_PIPELINE_CANARY_PROJECT_IDS="",
    )
    mode = resolver.resolve(
        project_id=1,
        project_config={"pipeline_mode": "legacy"},
        settings=settings,
    )
    assert mode == "legacy"


@pytest.mark.asyncio
async def test_router_honors_project_pipeline_mode_override():
    rag = MagicMock()
    rag.answer_question = AsyncMock(return_value=("legacy-path", None, None, False))
    settings = SimpleNamespace(
        RAG_PIPELINE_MODE="unified",
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
        unified_orchestrator=None,
        settings=settings,
    )
    project = SimpleNamespace(project_id=3, config_json={"pipeline_mode": "legacy"})
    profile = SimpleNamespace(domain_key="pharmacy")
    resp = await router.execute(
        project=project,
        query="q",
        limit=3,
        session_id=None,
        metadata_filter=None,
        profile=profile,
    )
    assert resp.answer == "legacy-path"
