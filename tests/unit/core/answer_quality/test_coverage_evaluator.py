"""Unit tests for DocIdCoverageEvaluator."""

from __future__ import annotations

import pytest

from core.answer_quality.coverage.evaluator import DocIdCoverageEvaluator
from tests.unit.core.answer_quality.conftest import (
    build_evidence_pack,
    build_golden_fixture,
    default_config,
)


@pytest.mark.asyncio
async def test_all_required_docs_present(default_config) -> None:
    fixture = build_golden_fixture(
        "q001",
        expected_source_ids=["doc-a", "doc-b"],
    )
    pack = build_evidence_pack(["doc-a", "doc-b"])

    result = await DocIdCoverageEvaluator().evaluate(fixture, pack, default_config)

    assert result.coverage_score == pytest.approx(1.0)
    assert result.passed is True
    assert result.missing_source_ids == []


@pytest.mark.asyncio
async def test_partial_match(default_config) -> None:
    fixture = build_golden_fixture(
        "q001",
        expected_source_ids=["doc-a", "doc-b", "doc-c"],
    )
    pack = build_evidence_pack(["doc-a"])

    result = await DocIdCoverageEvaluator().evaluate(fixture, pack, default_config)

    assert result.coverage_score == pytest.approx(1 / 3)
    assert set(result.missing_source_ids) == {"doc-b", "doc-c"}
    assert result.passed is False


@pytest.mark.asyncio
async def test_no_expected_source_ids_is_not_applicable(default_config) -> None:
    fixture = build_golden_fixture("q001", expected_source_ids=None)
    pack = build_evidence_pack(["doc-a"])

    result = await DocIdCoverageEvaluator().evaluate(fixture, pack, default_config)

    assert result.not_applicable is True
    assert result.passed is True
    assert result.coverage_score is None


@pytest.mark.asyncio
async def test_none_evidence_pack_is_not_applicable(default_config) -> None:
    fixture = build_golden_fixture("q001", expected_source_ids=["doc-a"])

    result = await DocIdCoverageEvaluator().evaluate(fixture, None, default_config)

    assert result.not_applicable is True
    assert result.passed is True
    assert result.coverage_score is None
