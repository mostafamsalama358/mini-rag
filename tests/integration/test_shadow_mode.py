"""Integration tests for shadow mode user-response parity."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.rag.pipeline.legacy_executor import LegacyPipelineExecutor
from services.rag.pipeline.models import (
    PipelineExecutionContext,
    PipelineSettingsSnapshot,
    UnifiedPipelineResult,
)
from services.rag.pipeline.router import PipelineRouter
from services.rag.pipeline.shadow_runner import ShadowRunner


def _settings(**overrides):
    base = dict(
        RAG_PIPELINE_MODE="shadow",
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


class _FakeUnified:
    async def execute(self, **kwargs):
        ctx = kwargs["ctx"]
        return UnifiedPipelineResult(
            execution_context=ctx,
            outcome="success",
            answer_result=SimpleNamespace(
                answer="unified-different",
                citations=[],
                no_answer=False,
            ),
        )


@pytest.mark.asyncio
async def test_shadow_returns_legacy_answer_not_unified():
    rag = MagicMock()
    rag.answer_question = AsyncMock(return_value=("legacy-answer", "p", None, False))
    settings = _settings()
    legacy = LegacyPipelineExecutor(rag_service=rag)
    shadow = ShadowRunner(
        legacy_executor=legacy,
        unified_orchestrator=_FakeUnified(),
        settings=settings,
    )
    router = PipelineRouter(
        legacy_executor=legacy,
        shadow_runner=shadow,
        settings=settings,
    )
    project = SimpleNamespace(project_id=1, config_json={})
    profile = SimpleNamespace(domain_key="pharmacy")
    resp = await router.execute(
        project=project,
        query="q",
        limit=5,
        session_id=None,
        metadata_filter=None,
        profile=profile,
    )
    assert resp.answer == "legacy-answer"
