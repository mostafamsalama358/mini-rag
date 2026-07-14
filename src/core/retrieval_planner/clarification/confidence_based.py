"""Confidence-based clarification detector."""

from __future__ import annotations

from core.query_parser.schema import ParseResult
from core.retrieval_planner.interfaces import IClarificationDetector
from core.retrieval_planner.models import QueryIntent, RetrievalPlannerConfig


class ConfidenceBasedClarificationDetector(IClarificationDetector):
    @property
    def detector_id(self) -> str:
        return "confidence_based"

    def detect(
        self,
        parse_result: ParseResult,
        intent: QueryIntent,
        config: RetrievalPlannerConfig,
    ) -> tuple[bool, str | None]:
        qp = parse_result.query_plan

        # Condition 1: upstream clarification flag
        if qp.needs_clarification:
            prompt = (qp.clarification_prompt or "").strip() or (
                "Could you clarify what you are looking for?"
            )
            return True, prompt

        # Condition 2: low intent confidence
        if intent.confidence < config.clarification_confidence_threshold:
            question = self._question_from_secondary(intent)
            return True, question

        # Condition 3: empty / whitespace-only query
        if not (parse_result.canonical_query or "").strip():
            return True, "Your query appears empty. What would you like to know?"

        return False, None

    @staticmethod
    def _question_from_secondary(intent: QueryIntent) -> str:
        if intent.secondary_categories:
            opts = ", ".join(intent.secondary_categories)
            return (
                f"I'm not sure whether you want a {intent.category} answer "
                f"or something else ({opts}). Could you clarify?"
            )
        return (
            f"I'm not confident about the intent of your query "
            f"(detected as {intent.category}). Could you rephrase?"
        )
