"""Filter extractor wrapping ParseResult.query_plan.filters + implicit language."""

from __future__ import annotations

from typing import Any

from core.query_parser.schema import ParseResult
from core.retrieval_planner.interfaces import IFilterExtractor
from core.retrieval_planner.models import (
    QueryFilter,
    RetrievalPlannerConfig,
    compute_filter_id,
)


class QueryPlanFilterExtractor(IFilterExtractor):
    @property
    def extractor_id(self) -> str:
        return "query_plan"

    def extract(
        self,
        parse_result: ParseResult,
        config: RetrievalPlannerConfig,
    ) -> list[QueryFilter]:
        del config
        results: list[QueryFilter] = []
        filters: dict[str, Any] = dict(parse_result.query_plan.filters or {})

        for field_name, value in filters.items():
            operator, filter_type, normalized = self._normalize(field_name, value)
            fid = compute_filter_id(filter_type, field_name, operator, normalized)
            results.append(
                QueryFilter(
                    filter_id=fid,
                    filter_type=filter_type,
                    field_name=field_name,
                    operator=operator,
                    value=normalized,
                    source="explicit",
                )
            )

        language = (parse_result.query_plan.language or "").strip().lower()
        if language:
            fid = compute_filter_id("language", "language", "eq", language)
            results.append(
                QueryFilter(
                    filter_id=fid,
                    filter_type="language",
                    field_name="language",
                    operator="eq",
                    value=language,
                    source="implicit",
                )
            )
        return results

    @staticmethod
    def _normalize(field_name: str, value: Any) -> tuple[str, str, Any]:
        """Return (operator, filter_type, value)."""
        if isinstance(value, dict) and "op" in value and "value" in value:
            return str(value["op"]), str(value.get("type", field_name)), value["value"]
        if isinstance(value, list):
            return "in", field_name, value
        # Heuristic filter_type from field name
        lower = field_name.lower()
        if "date" in lower or "time" in lower:
            ftype = "date"
        elif lower in ("language", "lang"):
            ftype = "language"
        elif "status" in lower:
            ftype = "status"
        elif "type" in lower:
            ftype = "document_type"
        else:
            ftype = "field"
        return "eq", ftype, value
