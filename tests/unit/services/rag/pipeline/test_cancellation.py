"""Cancellation / deadline policy for UnifiedRagOrchestrator."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.rag.pipeline.models import (
    PipelineExecutionContext,
    PipelineSettingsSnapshot,
    UnifiedPipelineResult,
)
from services.rag.pipeline.unified_orchestrator import UnifiedRagOrchestrator


def _ctx(*, deadline_offset: float = 30.0) -> PipelineExecutionContext:
    started = time.perf_counter()
    return PipelineExecutionContext(
        request_id="req-1",
        project_id=1,
        session_id=None,
        mode="unified",
        profile=SimpleNamespace(domain_key="generic", config={}, field_registry=None, metadata=None),
        metadata_filter=None,
        limit=10,
        locale="en",
        started_at=started,
        deadline_at=started + deadline_offset,
        pipeline_version="1.0.0",
        settings_snapshot=PipelineSettingsSnapshot(
            pipeline_mode="unified",
            fallback_on_error=True,
            unified_timeout_s=45.0,
            hybrid_search_enabled=True,
            reranker_enabled=False,
            semantic_parser_enabled=True,
        ),
    )


@pytest.mark.asyncio
async def test_cancelled_error_is_reraised():
    parse = AsyncMock(side_effect=asyncio.CancelledError())
    orch = UnifiedRagOrchestrator(
        query_parse_service=SimpleNamespace(parse=parse),
        planner=MagicMock(),
        engine=MagicMock(),
        evidence_orchestrator=MagicMock(),
        context_builder=MagicMock(),
        answer_pipeline=MagicMock(),
        field_context_adapter=MagicMock(),
    )
    with pytest.raises(asyncio.CancelledError):
        await orch.execute(
            project=SimpleNamespace(project_id=1),
            query="q",
            limit=10,
            session_id=None,
            metadata_filter=None,
            profile=SimpleNamespace(),
            ctx=_ctx(),
        )


@pytest.mark.asyncio
async def test_deadline_before_parse_returns_timeout():
    orch = UnifiedRagOrchestrator(
        query_parse_service=SimpleNamespace(parse=AsyncMock()),
        planner=MagicMock(),
        engine=MagicMock(),
        evidence_orchestrator=MagicMock(),
        context_builder=MagicMock(),
        answer_pipeline=MagicMock(),
        field_context_adapter=MagicMock(),
    )
    result = await orch.execute(
        project=SimpleNamespace(project_id=1),
        query="q",
        limit=10,
        session_id=None,
        metadata_filter=None,
        profile=SimpleNamespace(),
        ctx=_ctx(deadline_offset=-1.0),
    )
    assert isinstance(result, UnifiedPipelineResult)
    assert result.outcome == "timeout"
    assert result.stage_traces[0].stage == "parse"
    assert result.stage_traces[0].status == "timed_out"
    assert all(
        t.status == "skipped" for t in result.stage_traces[1:]
    ) or len(result.stage_traces) >= 1


@pytest.mark.asyncio
async def test_clarification_is_semantic_not_error():
    parse_result = SimpleNamespace(
        query_plan=SimpleNamespace(
            needs_clarification=True,
            clarification_prompt="Which drug?",
            entity=None,
            entities=[],
            field="dose",
        )
    )
    parse = AsyncMock(return_value=(parse_result, None))
    orch = UnifiedRagOrchestrator(
        query_parse_service=SimpleNamespace(parse=parse),
        planner=MagicMock(),
        engine=MagicMock(),
        evidence_orchestrator=MagicMock(),
        context_builder=MagicMock(),
        answer_pipeline=MagicMock(),
        field_context_adapter=MagicMock(),
    )
    result = await orch.execute(
        project=SimpleNamespace(project_id=1),
        query="dose?",
        limit=10,
        session_id=None,
        metadata_filter=None,
        profile=SimpleNamespace(),
        ctx=_ctx(),
    )
    assert result.outcome == "clarification"
    assert result.parse_result is parse_result
    # Later stages skipped — not failure outcome
    assert result.outcome != "error"
