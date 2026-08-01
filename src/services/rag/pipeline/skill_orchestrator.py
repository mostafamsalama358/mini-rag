"""Skill Runtime Orchestrator — unified Skill execution path (022)."""

from __future__ import annotations

import logging
from typing import Any

from models.db_schemes import Project
from services.FieldRegistry import FieldProfile
from services.rag.pipeline.builder.pipeline_builder import PipelineBuilder
from services.rag.pipeline.context import build_execution_context
from services.rag.pipeline.models import PipelineAnswerResponse, PipelineExecutionContext
from services.rag.pipeline.query_parse_service import QueryParseService
from services.rag.pipeline.response_adapter import ResponseAdapter
from services.rag.skills import SkillResolutionError, resolve_skill
from services.rag.skills.runtime_support import log_skill_bound, log_skill_parse
from services.rag.skills.stages.entity_parse_stage import EntityParseStage
from services.rag.skills.stages.formatting import FormattingStage
from services.rag.skills.stages.generation import GenerationStage
from services.rag.skills.stages.retrieval import RetrievalStage
from services.rag.skills.stages.validation import SkillValidationStage
from utils.metrics import RAG_CLARIFICATION_TOTAL

logger = logging.getLogger("uvicorn.error")


def profile_has_skills(profile: FieldProfile) -> bool:
    return bool(getattr(profile, "skills", None))


class SkillRuntimeOrchestrator:
    """Execute Skill-bound requests via declarative PipelineBuilder stages."""

    def __init__(
        self,
        *,
        db_client,
        nlp_controller,
        generation_client,
        template_parser,
        reranker=None,
        response_adapter: ResponseAdapter | None = None,
    ) -> None:
        self._db_client = db_client
        self._nlp_controller = nlp_controller
        self._generation_client = generation_client
        self._template_parser = template_parser
        self._reranker = reranker
        self._adapter = response_adapter or ResponseAdapter()
        self._parse_service = QueryParseService(
            generation_client=generation_client,
            db_client=db_client,
        )
        self._stages = self._build_stages()

    def _build_stages(self) -> tuple[Any, ...]:
        builder = PipelineBuilder()
        builder.register(EntityParseStage())
        builder.register(SkillValidationStage())
        builder.register(RetrievalStage())
        builder.register(GenerationStage())
        builder.register(FormattingStage())
        return builder.build()

    async def execute(
        self,
        *,
        project: Project,
        query: str,
        limit: int,
        session_id: str | None,
        metadata_filter: dict[str, Any] | None,
        profile: FieldProfile,
        ctx: PipelineExecutionContext | None = None,
        skill_id: str | None = None,
    ) -> PipelineAnswerResponse:
        project_label = str(getattr(project, "project_id", "unknown"))

        try:
            skill_ctx = resolve_skill(profile, skill_id)
        except SkillResolutionError as exc:
            RAG_CLARIFICATION_TOTAL.labels(project_id=project_label).inc()
            return FormattingStage.clarification_response(str(exc))

        if skill_ctx is None:
            raise RuntimeError("SkillRuntimeOrchestrator invoked for non-Skill profile")

        log_skill_bound(project_label, skill_ctx)

        pipeline_ctx = ctx
        if pipeline_ctx is None:
            pipeline_ctx = build_execution_context(
                project_id=int(project.project_id),
                profile=profile,
                limit=limit,
                session_id=session_id,
                metadata_filter=metadata_filter,
                skill_id=skill_id,
                skill_ctx=skill_ctx,
            )
        elif pipeline_ctx.skill_ctx is None:
            pipeline_ctx = pipeline_ctx.model_copy(
                update={"skill_id": skill_id, "skill_ctx": skill_ctx}
            )

        entity_parse, validation, retrieval, generation, formatting = self._stages

        parse_result = await entity_parse.execute(
            pipeline_ctx,
            query=query,
            project=project,
            profile=profile,
            skill_ctx=skill_ctx,
            generation_client=self._generation_client,
            parse_service=self._parse_service,
        )
        if parse_result.status != "completed":
            return FormattingStage.clarification_response(parse_result.error)

        skill_ctx = parse_result.payload["skill_ctx"]
        entity_result = parse_result.payload["entity_result"]
        log_skill_parse(project_label, profile.domain_key, entity_result)

        validation_result = await validation.execute(
            pipeline_ctx,
            skill_ctx=skill_ctx,
            query=query,
        )
        if validation_result.status == "clarification":
            RAG_CLARIFICATION_TOTAL.labels(project_id=project_label).inc()
            return FormattingStage.clarification_response(
                validation_result.payload.get("clarification")
            )
        if validation_result.status != "completed":
            return FormattingStage.clarification_response(validation_result.error)

        retrieval_result = await retrieval.execute(
            pipeline_ctx,
            skill_ctx=skill_ctx,
            query=query,
            project=project,
            profile=profile,
            limit=limit,
            metadata_filter=metadata_filter,
            entity_result=entity_result,
            nlp_controller=self._nlp_controller,
            db_client=self._db_client,
            reranker=self._reranker,
        )
        if retrieval_result.status in ("no_context", "clarification"):
            return FormattingStage.from_stage_payload(retrieval_result.payload)
        if retrieval_result.status != "completed":
            return FormattingStage.clarification_response(retrieval_result.error)

        generation_result = await generation.execute(
            pipeline_ctx,
            skill_ctx=skill_ctx,
            query=query,
            project=project,
            profile=profile,
            parse_result=retrieval_result.payload["parse_result"],
            query_plan=retrieval_result.payload["query_plan"],
            retrieval=retrieval_result.payload["retrieval"],
            documents=retrieval_result.payload["documents"],
            generation_client=self._generation_client,
            template_parser=self._template_parser,
        )
        if generation_result.status != "completed":
            return FormattingStage.clarification_response(generation_result.error)

        format_result = await formatting.execute(
            pipeline_ctx,
            **generation_result.payload,
        )
        if format_result.status != "completed":
            return FormattingStage.clarification_response(format_result.error)

        response: PipelineAnswerResponse = format_result.payload["response"]
        if response.needs_clarification:
            RAG_CLARIFICATION_TOTAL.labels(project_id=project_label).inc()
        return response

    async def execute_as_legacy_tuple(
        self,
        **kwargs: Any,
    ) -> tuple[str | None, str | None, list | None, bool]:
        """Facade for direct RAGService.answer_question Skill delegation."""
        response = await self.execute(**kwargs)
        return (
            response.answer,
            response.full_prompt,
            response.chat_history,
            response.needs_clarification,
        )
