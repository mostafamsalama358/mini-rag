"""Skill validation stage — clarify on rule failure (022)."""

from __future__ import annotations

from typing import Any

from services.rag.skills import evaluate_skill_validation
from services.rag.skills.stages.contracts import StageResult


class SkillValidationStage:
    name = "skill_validation"

    async def execute(self, ctx: Any, **kwargs: Any) -> StageResult:
        skill_ctx = kwargs.get("skill_ctx") or getattr(ctx, "skill_ctx", None)
        original_query = kwargs.get("query") or ""
        if skill_ctx is None:
            return StageResult(
                stage=self.name,
                status="failed",
                error="missing_skill_ctx",
            )

        has_need = bool(getattr(skill_ctx, "need_text", None)) or (
            skill_ctx.recommend_mode and bool((original_query or "").strip())
        )
        ok, clarify = evaluate_skill_validation(
            skill_ctx.skill,
            list(skill_ctx.entities),
            has_need_frame=has_need,
        )
        if not ok:
            return StageResult(
                stage=self.name,
                status="clarification",
                payload={"clarification": clarify, "needs_clarification": True},
            )
        return StageResult(
            stage=self.name,
            status="completed",
            payload={"validated": True},
        )
