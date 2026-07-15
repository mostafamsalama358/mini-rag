"""Keyword overlap completeness scorer."""

from __future__ import annotations

import re

from core.answer_generation.models import AnswerResult
from core.answer_quality.config import AnswerQualityConfig
from core.answer_quality.interfaces import ICompletenessScorer
from core.answer_quality.models import CompletenessResult, GoldenTestFixture

_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "to",
        "of",
        "in",
        "on",
        "for",
        "and",
        "or",
        "if",
        "with",
        "at",
        "by",
        "from",
        "as",
        "be",
        "this",
        "that",
        "it",
    }
)


def _effective_completeness_threshold(
    fixture: GoldenTestFixture,
    config: AnswerQualityConfig,
) -> float:
    if fixture.thresholds is not None and fixture.thresholds.completeness is not None:
        return fixture.thresholds.completeness
    if config.global_thresholds.completeness is not None:
        return config.global_thresholds.completeness
    return 0.7


def _tokenise(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {token for token in tokens if token not in _STOP_WORDS}


def _facet_covered(
    facet: str,
    answer_tokens: set[str],
    overlap_threshold: float,
) -> bool:
    facet_tokens = _tokenise(facet)
    if not facet_tokens:
        return False
    overlap = len(facet_tokens & answer_tokens) / len(facet_tokens)
    return overlap >= overlap_threshold


class KeywordCompletenessScorer(ICompletenessScorer):
    async def score(
        self,
        fixture: GoldenTestFixture,
        answer_result: AnswerResult,
        config: AnswerQualityConfig,
    ) -> CompletenessResult:
        facets = fixture.expected_answer_facets
        if not facets or answer_result.no_answer:
            return CompletenessResult(
                question_id=fixture.question_id,
                completeness_score=None,
                not_applicable=True,
                passed=True,
            )

        answer_tokens = _tokenise(answer_result.answer)
        covered: list[str] = []
        uncovered: list[str] = []
        for facet in facets:
            if _facet_covered(facet, answer_tokens, config.completeness_overlap_threshold):
                covered.append(facet)
            else:
                uncovered.append(facet)

        score = len(covered) / len(facets)
        threshold = _effective_completeness_threshold(fixture, config)
        passed = score >= threshold

        return CompletenessResult(
            question_id=fixture.question_id,
            completeness_score=score,
            covered_facets=covered,
            uncovered_facets=uncovered,
            not_applicable=False,
            passed=passed,
        )
