"""Answer Generation pluggable interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.answer_generation.config import AnswerGenerationConfig
from core.answer_generation.models import (
    CitationReference,
    ComposedPrompt,
    GroundingFlag,
)
from core.context_builder.models import Context
from core.evidence_orchestrator.models import Citation


class IPromptComposer(ABC):
    @abstractmethod
    def compose(
        self,
        context: Context,
        question: str,
        config: AnswerGenerationConfig,
    ) -> ComposedPrompt: ...


class IOutputParser(ABC):
    @abstractmethod
    def parse(
        self,
        raw: str,
        config: AnswerGenerationConfig,
    ) -> tuple[str, str | None]: ...


class ICitationFormatter(ABC):
    @abstractmethod
    def format(
        self,
        answer_text: str,
        citation_map: dict[str, Citation],
    ) -> list[CitationReference]: ...


class IGroundingChecker(ABC):
    @abstractmethod
    def check(
        self,
        answer_text: str,
        context: Context,
    ) -> list[GroundingFlag]: ...
