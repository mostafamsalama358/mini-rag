"""Document-ID coverage evaluator."""

from __future__ import annotations

from core.answer_quality.config import AnswerQualityConfig
from core.answer_quality.interfaces import ICoverageEvaluator
from core.answer_quality.models import CoverageResult, GoldenTestFixture
from core.evidence_orchestrator.models import EvidencePack


def _effective_coverage_threshold(
    fixture: GoldenTestFixture,
    config: AnswerQualityConfig,
) -> float:
    if fixture.thresholds is not None and fixture.thresholds.coverage is not None:
        return fixture.thresholds.coverage
    if config.global_thresholds.coverage is not None:
        return config.global_thresholds.coverage
    return 0.8


class DocIdCoverageEvaluator(ICoverageEvaluator):
    async def evaluate(
        self,
        fixture: GoldenTestFixture,
        evidence_pack: EvidencePack | None,
        config: AnswerQualityConfig,
    ) -> CoverageResult:
        expected = fixture.expected_source_ids
        if not expected or evidence_pack is None:
            return CoverageResult(
                question_id=fixture.question_id,
                coverage_score=None,
                not_applicable=True,
                passed=True,
            )

        actual = {item.doc_id for item in evidence_pack.items}
        expected_set = set(expected)
        found = sorted(expected_set & actual)
        missing = sorted(expected_set - actual)
        score = len(found) / len(expected_set)
        threshold = _effective_coverage_threshold(fixture, config)
        passed = score >= threshold

        return CoverageResult(
            question_id=fixture.question_id,
            coverage_score=score,
            missing_source_ids=missing,
            found_source_ids=found,
            not_applicable=False,
            passed=passed,
        )
