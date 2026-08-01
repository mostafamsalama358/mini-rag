"""Thin legacy executor wrapping RAGService.answer_question."""

from __future__ import annotations

from typing import Any

from models.db_schemes import Project
from services.FieldRegistry import FieldProfile
from services.rag.answer_service import RAGService
from services.rag.pipeline.models import PipelineAnswerResponse, PipelineExecutionContext
from services.rag.pipeline.response_adapter import ResponseAdapter


class LegacyPipelineExecutor:
    """Wraps existing RAGService without modifying legacy behavior."""

    def __init__(
        self,
        *,
        rag_service: RAGService,
        response_adapter: ResponseAdapter | None = None,
    ) -> None:
        self._rag_service = rag_service
        self._adapter = response_adapter or ResponseAdapter()

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
        skill_id: str | None = None,
    ) -> PipelineAnswerResponse:
        _ = ctx
        answer, full_prompt, chat_history, needs_clarification = await self._rag_service.answer_question(
            project=project,
            query=query,
            limit=limit,
            session_id=session_id,
            metadata_filter=metadata_filter,
            profile=profile,
            skill_id=skill_id,
        )
        return self._adapter.from_legacy_tuple(
            answer,
            full_prompt,
            chat_history,
            needs_clarification,
        )
