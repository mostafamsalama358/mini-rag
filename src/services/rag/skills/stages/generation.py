"""Skill-owned answer generation stage (022)."""

from __future__ import annotations

from typing import Any

from services.rag.skills.runtime_support import generate_skill_answer
from services.rag.skills.stages.contracts import StageResult


class GenerationStage:
    name = "generation"

    async def execute(self, ctx: Any, **kwargs: Any) -> StageResult:
        skill_ctx = kwargs.get("skill_ctx") or getattr(ctx, "skill_ctx", None)
        if skill_ctx is None:
            return StageResult(stage=self.name, status="failed", error="missing_skill_ctx")

        project = kwargs["project"]
        original_query = kwargs["query"]
        profile = kwargs["profile"]
        parse_result = kwargs["parse_result"]
        query_plan = kwargs["query_plan"]
        retrieval = kwargs["retrieval"]
        documents = kwargs["documents"]
        generation_client = kwargs["generation_client"]
        template_parser = kwargs["template_parser"]
        project_label = str(getattr(project, "project_id", "unknown"))

        answer, full_prompt, chat_history, needs_clarification = await generate_skill_answer(
            project_label=project_label,
            original_query=original_query,
            parse_result=parse_result,
            query_plan=query_plan,
            profile=profile,
            skill_ctx=skill_ctx,
            retrieved_documents=documents,
            field_is_list=retrieval.field_is_list,
            generation_client=generation_client,
            template_parser=template_parser,
        )

        return StageResult(
            stage=self.name,
            status="completed",
            payload={
                "answer": answer,
                "full_prompt": full_prompt,
                "chat_history": chat_history,
                "needs_clarification": needs_clarification,
            },
        )
