"""Answer Quality domain errors."""

from __future__ import annotations


class AnswerQualityError(Exception):
    """Base error for the answer quality evaluation layer."""


class EvaluationError(AnswerQualityError):
    """Fatal evaluation failure (empty fixtures, invalid run state)."""


class FixtureLoadError(AnswerQualityError):
    """Golden fixture YAML failed schema validation."""


class RunNotFoundError(AnswerQualityError):
    """Requested evaluation run ID was not found in the store."""


class UnmatchedQuestionError(AnswerQualityError):
    """Fixture question has no matching pipeline snapshot."""
