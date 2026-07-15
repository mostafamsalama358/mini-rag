"""Answer Quality evaluation layer."""

from core.answer_quality.config import (
    AnswerQualityConfig,
    load_config_from_yaml,
    merge_config,
    resolve_answer_quality_config,
)
from core.answer_quality.errors import (
    AnswerQualityError,
    EvaluationError,
    FixtureLoadError,
    RunNotFoundError,
    UnmatchedQuestionError,
)
from core.answer_quality.interfaces import (
    ICompletenessScorer,
    ICoverageEvaluator,
    IFaithfulnessScorer,
    IGoldenTestRunner,
    IRegressionStore,
)
from core.answer_quality.models import (
    SCHEMA_VERSION,
    CompletenessResult,
    CoverageResult,
    EvaluationResult,
    FaithfulnessResult,
    GoldenTestFixture,
    GoldenTestResult,
    PipelineSnapshot,
    QuestionDelta,
    RegressionDiff,
    ScoreThresholds,
)
from core.answer_quality.registry import AnswerQualityRegistry

__all__ = [
    "SCHEMA_VERSION",
    "AnswerQualityConfig",
    "AnswerQualityError",
    "AnswerQualityRegistry",
    "CompletenessResult",
    "CoverageResult",
    "EvaluationError",
    "EvaluationResult",
    "FaithfulnessResult",
    "FixtureLoadError",
    "GoldenTestFixture",
    "GoldenTestResult",
    "ICompletenessScorer",
    "ICoverageEvaluator",
    "IFaithfulnessScorer",
    "IGoldenTestRunner",
    "IRegressionStore",
    "PipelineSnapshot",
    "QuestionDelta",
    "RegressionDiff",
    "RunNotFoundError",
    "ScoreThresholds",
    "UnmatchedQuestionError",
    "load_config_from_yaml",
    "merge_config",
    "resolve_answer_quality_config",
]
