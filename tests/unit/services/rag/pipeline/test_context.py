"""Unit tests for pipeline context builder and models."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.rag.pipeline.context import build_execution_context, build_settings_snapshot
from services.rag.pipeline.models import PipelineAnswerResponse, PipelineStageTrace


def _settings(**overrides):
    base = {
        "RAG_PIPELINE_MODE": "legacy",
        "RAG_PIPELINE_FALLBACK_ON_ERROR": True,
        "RAG_PIPELINE_UNIFIED_TIMEOUT_S": 45.0,
        "RAG_PIPELINE_SHADOW_DIVERGENCE_THRESHOLD": 0.85,
        "RAG_PIPELINE_CANARY_PROJECT_IDS": "",
        "RAG_ENABLE_HYBRID_SEARCH": True,
        "RAG_ENABLE_RERANKER": True,
        "RAG_SEMANTIC_PARSER_ENABLED": True,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_execution_context_carries_skill_fields():
    skill_ctx = SimpleNamespace(skill_id="leaflet")
    ctx = build_execution_context(
        project_id=3,
        profile=SimpleNamespace(domain_key="pharmacy"),
        limit=10,
        mode="legacy",
        locale="en",
        settings=_settings(),
        skill_id="leaflet",
        skill_ctx=skill_ctx,
    )
    assert ctx.skill_id == "leaflet"
    assert ctx.skill_ctx is skill_ctx


def test_build_execution_context_is_frozen():
    ctx = build_execution_context(
        project_id=3,
        profile=SimpleNamespace(domain_key="pharmacy"),
        limit=10,
        mode="legacy",
        locale="ar",
        settings=_settings(),
    )
    assert ctx.project_id == 3
    assert ctx.locale == "ar"
    assert ctx.pipeline_version == "1.0.0"
    assert ctx.deadline_at == ctx.started_at + 45.0
    with pytest.raises(Exception):
        ctx.mode = "unified"  # type: ignore[misc]


def test_build_settings_snapshot_rejects_bad_timeout():
    with pytest.raises(ValueError):
        build_settings_snapshot(mode="legacy", settings=_settings(RAG_PIPELINE_UNIFIED_TIMEOUT_S=0))


def test_stage_trace_and_answer_response_construct():
    trace = PipelineStageTrace(
        stage="parse",
        status="completed",
        started_at=1.0,
        duration_ms=12.5,
    )
    assert trace.stage == "parse"
    resp = PipelineAnswerResponse(answer="hi", needs_clarification=False)
    assert resp.signal.value == "rag_answer_success"
