"""Retrieval Planner strategy interfaces (pluggable ABCs)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.query_parser.schema import ParseResult
from core.retrieval_planner.models import (
    QueryFilter,
    QueryIntent,
    ResolvedEntity,
    RetrievalPlan,
    RetrievalPlannerConfig,
    StrategyType,
)


class IRetrievalPlanner(ABC):
    @abstractmethod
    def plan(
        self,
        parse_result: ParseResult,
        config: RetrievalPlannerConfig,
    ) -> RetrievalPlan: ...


class IIntentClassifier(ABC):
    @property
    @abstractmethod
    def classifier_id(self) -> str: ...

    @abstractmethod
    def classify(
        self,
        parse_result: ParseResult,
        config: RetrievalPlannerConfig,
    ) -> QueryIntent: ...


class IEntityResolver(ABC):
    @property
    @abstractmethod
    def resolver_id(self) -> str: ...

    @abstractmethod
    def resolve(
        self,
        parse_result: ParseResult,
        config: RetrievalPlannerConfig,
    ) -> list[ResolvedEntity]: ...


class IFilterExtractor(ABC):
    @property
    @abstractmethod
    def extractor_id(self) -> str: ...

    @abstractmethod
    def extract(
        self,
        parse_result: ParseResult,
        config: RetrievalPlannerConfig,
    ) -> list[QueryFilter]: ...


class IStrategySelector(ABC):
    @property
    @abstractmethod
    def selector_id(self) -> str: ...

    @abstractmethod
    def select(
        self,
        intent: QueryIntent,
        entities: list[ResolvedEntity],
        filters: list[QueryFilter],
        config: RetrievalPlannerConfig,
    ) -> list[StrategyType]: ...


class IClarificationDetector(ABC):
    @property
    @abstractmethod
    def detector_id(self) -> str: ...

    @abstractmethod
    def detect(
        self,
        parse_result: ParseResult,
        intent: QueryIntent,
        config: RetrievalPlannerConfig,
    ) -> tuple[bool, str | None]: ...
