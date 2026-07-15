"""Answer Quality interface contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from core.answer_generation.models import AnswerResult
from core.answer_quality.config import AnswerQualityConfig
from core.answer_quality.models import (
    CompletenessResult,
    CoverageResult,
    EvaluationResult,
    FaithfulnessResult,
    GoldenTestFixture,
    PipelineSnapshot,
    RegressionDiff,
)
from core.context_builder.models import Context
from core.evidence_orchestrator.models import EvidencePack


class ICoverageEvaluator(ABC):
    @abstractmethod
    async def evaluate(
        self,
        fixture: GoldenTestFixture,
        evidence_pack: EvidencePack | None,
        config: AnswerQualityConfig,
    ) -> CoverageResult: ...


class IFaithfulnessScorer(ABC):
    @abstractmethod
    async def score(
        self,
        fixture: GoldenTestFixture,
        answer_result: AnswerResult,
        context: Context,
        config: AnswerQualityConfig,
    ) -> FaithfulnessResult: ...


class ICompletenessScorer(ABC):
    @abstractmethod
    async def score(
        self,
        fixture: GoldenTestFixture,
        answer_result: AnswerResult,
        config: AnswerQualityConfig,
    ) -> CompletenessResult: ...


class IGoldenTestRunner(ABC):
    @abstractmethod
    async def run(
        self,
        fixtures: list[GoldenTestFixture],
        pipeline_outputs: list[PipelineSnapshot],
        config: AnswerQualityConfig,
        *,
        fixture_file: str = "",
    ) -> EvaluationResult: ...


class IRegressionStore(ABC):
    @abstractmethod
    async def save(self, result: EvaluationResult) -> Path: ...

    @abstractmethod
    async def load(self, run_id: str) -> EvaluationResult: ...

    @abstractmethod
    async def list_runs(self) -> list[str]: ...

    @abstractmethod
    async def diff(
        self,
        run_id_baseline: str,
        run_id_current: str,
        config: AnswerQualityConfig,
    ) -> RegressionDiff: ...
