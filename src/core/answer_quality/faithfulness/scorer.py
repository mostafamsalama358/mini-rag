"""Text-matching faithfulness scorer."""

from __future__ import annotations

import re

from core.answer_generation.models import AnswerResult
from core.answer_quality.config import AnswerQualityConfig
from core.answer_quality.interfaces import IFaithfulnessScorer
from core.answer_quality.models import FaithfulnessResult, GoldenTestFixture
from core.context_builder.models import Context

_NUMBER_PATTERN = re.compile(r"\d+[\.,]?\d*\s*\w*")
_TITLE_CASE_PATTERN = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b")
_QUOTED_PATTERN = re.compile(r'"([^"]+)"|\'([^\']+)\'')


def _effective_faithfulness_threshold(
    fixture: GoldenTestFixture,
    config: AnswerQualityConfig,
) -> float:
    if fixture.thresholds is not None and fixture.thresholds.faithfulness is not None:
        return fixture.thresholds.faithfulness
    if config.global_thresholds.faithfulness is not None:
        return config.global_thresholds.faithfulness
    return 0.8


def _extract_claim_spans(answer: str) -> list[str]:
    spans: list[str] = []
    for match in _NUMBER_PATTERN.finditer(answer):
        spans.append(match.group(0).strip())
    for match in _TITLE_CASE_PATTERN.finditer(answer):
        spans.append(match.group(0).strip())
    for match in _QUOTED_PATTERN.finditer(answer):
        quoted = match.group(1) or match.group(2)
        if quoted:
            spans.append(quoted.strip())
    return spans


class TextFaithfulnessScorer(IFaithfulnessScorer):
    async def score(
        self,
        fixture: GoldenTestFixture,
        answer_result: AnswerResult,
        context: Context,
        config: AnswerQualityConfig,
    ) -> FaithfulnessResult:
        if (
            answer_result.no_answer
            or not context.ordered_blocks
            or not answer_result.answer.strip()
        ):
            return FaithfulnessResult(
                question_id=fixture.question_id,
                faithfulness_score=None,
                not_applicable=True,
                passed=True,
            )

        source_corpus = " ".join(
            block.text.lower() for block in context.ordered_blocks
        )
        spans = _extract_claim_spans(answer_result.answer)
        unsupported = [
            span for span in spans if span.lower() not in source_corpus
        ]
        total = max(len(spans), 1)
        score = 1.0 - (len(unsupported) / total)
        threshold = _effective_faithfulness_threshold(fixture, config)
        passed = score >= threshold

        return FaithfulnessResult(
            question_id=fixture.question_id,
            faithfulness_score=score,
            unsupported_claims=unsupported,
            total_spans_checked=len(spans),
            not_applicable=False,
            passed=passed,
        )
