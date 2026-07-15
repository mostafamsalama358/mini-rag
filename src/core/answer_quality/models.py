"""Answer Quality domain models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.answer_generation.models import AnswerResult
from core.context_builder.models import Context
from core.evidence_orchestrator.models import EvidencePack

SCHEMA_VERSION = "1.0.0"


class ScoreThresholds(BaseModel):
    model_config = ConfigDict(frozen=True)

    coverage: float | None = Field(default=0.8, ge=0.0, le=1.0)
    faithfulness: float | None = Field(default=0.8, ge=0.0, le=1.0)
    completeness: float | None = Field(default=0.7, ge=0.0, le=1.0)


class GoldenTestFixture(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    expected_source_ids: list[str] | None = None
    expected_answer_facets: list[str] | None = None
    thresholds: ScoreThresholds | None = None


@dataclass(frozen=True)
class PipelineSnapshot:
    question_id: str
    answer_result: AnswerResult
    context: Context
    evidence_pack: EvidencePack | None


class PipelineSnapshotRecord(BaseModel):
    """JSON-serialisable envelope for PipelineSnapshot persistence."""

    model_config = ConfigDict(frozen=True)

    question_id: str = Field(min_length=1)
    answer_result: AnswerResult
    context: Context
    evidence_pack: EvidencePack | None = None

    def to_snapshot(self) -> PipelineSnapshot:
        return PipelineSnapshot(
            question_id=self.question_id,
            answer_result=self.answer_result,
            context=self.context,
            evidence_pack=self.evidence_pack,
        )

    @classmethod
    def from_snapshot(cls, snapshot: PipelineSnapshot) -> PipelineSnapshotRecord:
        return cls(
            question_id=snapshot.question_id,
            answer_result=snapshot.answer_result,
            context=snapshot.context,
            evidence_pack=snapshot.evidence_pack,
        )


class CoverageResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str = Field(min_length=1)
    coverage_score: float | None = None
    missing_source_ids: list[str] = Field(default_factory=list)
    found_source_ids: list[str] = Field(default_factory=list)
    not_applicable: bool = False
    passed: bool = False


class FaithfulnessResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str = Field(min_length=1)
    faithfulness_score: float | None = None
    unsupported_claims: list[str] = Field(default_factory=list)
    total_spans_checked: int = Field(default=0, ge=0)
    not_applicable: bool = False
    passed: bool = False


class CompletenessResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str = Field(min_length=1)
    completeness_score: float | None = None
    covered_facets: list[str] = Field(default_factory=list)
    uncovered_facets: list[str] = Field(default_factory=list)
    not_applicable: bool = False
    passed: bool = False


class GoldenTestResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    coverage: CoverageResult
    faithfulness: FaithfulnessResult
    completeness: CompletenessResult
    passed: bool
    evaluated_at: str = Field(min_length=1)


class EvaluationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str = Field(min_length=1)
    run_at: str = Field(min_length=1)
    question_results: list[GoldenTestResult] = Field(default_factory=list)
    aggregate_pass_rate: float = Field(ge=0.0, le=1.0)
    aggregate_coverage: float | None = None
    aggregate_faithfulness: float | None = None
    aggregate_completeness: float | None = None
    passed: bool
    fixture_file: str = ""
    schema_version: str = SCHEMA_VERSION

    @field_validator("schema_version")
    @classmethod
    def _schema_major_version(cls, value: str) -> str:
        expected_major = SCHEMA_VERSION.split(".", maxsplit=1)[0]
        actual_major = value.split(".", maxsplit=1)[0]
        if expected_major != actual_major:
            raise ValueError(
                f"schema_version major {actual_major!r} must match {expected_major!r}"
            )
        return value


DimensionName = Literal["coverage", "faithfulness", "completeness", "overall"]


class QuestionDelta(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str = Field(min_length=1)
    dimension: DimensionName
    baseline_score: float | None = None
    current_score: float | None = None
    delta: float | None = None


class RegressionDiff(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id_baseline: str = Field(min_length=1)
    run_id_current: str = Field(min_length=1)
    regressions: list[QuestionDelta] = Field(default_factory=list)
    improvements: list[QuestionDelta] = Field(default_factory=list)
    stable: list[str] = Field(default_factory=list)
    has_regressions: bool = False
