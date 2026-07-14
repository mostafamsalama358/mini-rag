"""Rule-based intent classifier — operation mapping + text pattern augmentation."""

from __future__ import annotations

import re

from core.query_parser.schema import ParseResult
from core.retrieval_planner.interfaces import IIntentClassifier
from core.retrieval_planner.models import IntentCategory, QueryIntent, RetrievalPlannerConfig

_OPERATION_MAP: dict[str, IntentCategory] = {
    "lookup": "factual",
    "list": "list",
    "compare": "comparative",
    "explain": "procedural",
    "count": "factual",
}

_PATTERNS: list[tuple[re.Pattern[str], IntentCategory]] = [
    (re.compile(r"\b(table|tabular|row|column|schedule)\b", re.I), "tabular"),
    (re.compile(r"\b(how to|steps|procedure|process)\b", re.I), "procedural"),
    (re.compile(r"\b(compare|versus|vs\.?|difference between)\b", re.I), "comparative"),
    (re.compile(r"\b(navigate|find|where is|location of)\b", re.I), "navigational"),
]


class RuleBasedIntentClassifier(IIntentClassifier):
    @property
    def classifier_id(self) -> str:
        return "rule_based"

    def classify(
        self,
        parse_result: ParseResult,
        config: RetrievalPlannerConfig,
    ) -> QueryIntent:
        del config
        qp = parse_result.query_plan
        query = parse_result.canonical_query or ""
        operation = qp.operation

        pattern_hits: list[tuple[IntentCategory, str]] = []
        for pattern, category in _PATTERNS:
            m = pattern.search(query)
            if m:
                pattern_hits.append((category, m.group(0)))

        pattern_categories = {c for c, _ in pattern_hits}
        multi_list = bool(re.search(r"\blist\b", query, re.I))

        if operation == "unsupported":
            return self._classify_unsupported(pattern_hits, pattern_categories)

        base: IntentCategory = _OPERATION_MAP[operation]
        evidence: list[str] = [operation]
        for _, matched in pattern_hits:
            evidence.append(matched)

        # Mixed: comparative operation + list keyword, or multiple distinct pattern cats
        if base == "comparative" and multi_list:
            secondary = sorted(
                (pattern_categories | {"list", "comparative"}) - {"mixed"}
            )
            return QueryIntent(
                category="mixed",
                confidence=0.8,
                secondary_categories=tuple(  # type: ignore[arg-type]
                    c for c in secondary if c != "mixed"
                ),
                evidence=tuple(evidence + ["multi-signal"]),
            )

        # Pass 2 override from first non-matching pattern
        override: IntentCategory | None = None
        for cat, _ in pattern_hits:
            if cat == "procedural" and base == "comparative":
                continue
            if cat != base:
                override = cat
                break

        if override is not None:
            return QueryIntent(
                category=override,
                confidence=0.8,
                secondary_categories=(base,),
                evidence=tuple(evidence),
            )

        return QueryIntent(
            category=base,
            confidence=1.0,
            secondary_categories=(),
            evidence=tuple(evidence),
        )

    @staticmethod
    def _classify_unsupported(
        pattern_hits: list[tuple[IntentCategory, str]],
        pattern_categories: set[IntentCategory],
    ) -> QueryIntent:
        if not pattern_hits:
            return QueryIntent(
                category="factual",
                confidence=0.4,
                secondary_categories=(),
                evidence=(),
            )
        if len(pattern_categories) > 1:
            secondary = sorted(pattern_categories)
            return QueryIntent(
                category="mixed",
                confidence=0.6,
                secondary_categories=tuple(secondary),  # type: ignore[arg-type]
                evidence=tuple(e for _, e in pattern_hits),
            )
        category = pattern_hits[0][0]
        return QueryIntent(
            category=category,
            confidence=0.6,
            secondary_categories=(),
            evidence=tuple(e for _, e in pattern_hits),
        )
