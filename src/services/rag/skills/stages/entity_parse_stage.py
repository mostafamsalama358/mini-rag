"""Entity-only parse stage for Skill-bound requests (022)."""

from __future__ import annotations

from typing import Any

from services.rag.skills import entity_parse_async
from services.rag.skills.stages.contracts import StageResult


class EntityParseStage:
    name = "entity_parse"

    async def execute(self, ctx: Any, **kwargs: Any) -> StageResult:
        skill_ctx = kwargs.get("skill_ctx") or getattr(ctx, "skill_ctx", None)
        if skill_ctx is None:
            return StageResult(stage=self.name, status="failed", error="missing_skill_ctx")

        query = kwargs["query"]
        profile = kwargs["profile"]
        project = kwargs["project"]
        generation_client = kwargs.get("generation_client")
        parse_service = kwargs.get("parse_service")
        if parse_service is None:
            return StageResult(stage=self.name, status="failed", error="missing_parse_service")

        catalog_terms, fingerprint_index = await parse_service._load_catalog_for_parser(
            project, profile
        )
        entity_result = await entity_parse_async(
            query,
            profile=profile,
            generation_client=generation_client,
            catalog_terms=catalog_terms or None,
            catalog_fingerprint_index=fingerprint_index or None,
        )
        updated_skill_ctx = skill_ctx.with_entities(
            entity_result.entities,
            slots=entity_result.slots,
            need_text=entity_result.need_text,
        )
        return StageResult(
            stage=self.name,
            status="completed",
            payload={
                "skill_ctx": updated_skill_ctx,
                "entity_result": entity_result,
            },
        )
