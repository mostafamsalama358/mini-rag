"""Entity resolver wrapping ParseResult.query_plan.entities."""

from __future__ import annotations

import re

from core.query_parser.schema import ParseResult
from core.retrieval_planner.interfaces import IEntityResolver
from core.retrieval_planner.models import (
    ResolvedEntity,
    RetrievalPlannerConfig,
    compute_entity_id,
)


class QueryPlanEntityResolver(IEntityResolver):
    @property
    def resolver_id(self) -> str:
        return "query_plan"

    def resolve(
        self,
        parse_result: ParseResult,
        config: RetrievalPlannerConfig,
    ) -> list[ResolvedEntity]:
        raw_entities = list(parse_result.query_plan.entities or [])
        # Also include singular entity field if present and not already listed
        singular = parse_result.query_plan.entity
        if singular and singular not in raw_entities:
            raw_entities.insert(0, singular)

        results: list[ResolvedEntity] = []
        for raw in raw_entities:
            if not (raw or "").strip():
                continue
            canonical = config.entity_aliases.get(raw, raw)
            entity_type = self._match_type(canonical, config.entity_type_patterns)
            entity_id = compute_entity_id(canonical, entity_type)
            span = self._find_span(parse_result.canonical_query, raw)
            results.append(
                ResolvedEntity(
                    entity_id=entity_id,
                    raw_text=raw,
                    canonical_form=canonical,
                    entity_type=entity_type,
                    source_span=span,
                )
            )
        return results

    @staticmethod
    def _match_type(text: str, patterns: list[dict[str, str]]) -> str:
        lower = text.lower()
        for rule in patterns:
            pat = rule.get("pattern", "")
            etype = rule.get("entity_type", "concept")
            if pat and re.search(pat, lower, re.I):
                return etype
        return "concept"

    @staticmethod
    def _find_span(query: str, raw: str) -> tuple[int, int] | None:
        if not query or not raw:
            return None
        idx = query.lower().find(raw.lower())
        if idx < 0:
            return None
        return (idx, idx + len(raw))
