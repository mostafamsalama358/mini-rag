"""Retrieval Engine pluggable interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.retrieval_engine.models import (
    ExpansionContext,
    ExpansionResult,
    RawCandidate,
    RetrievalContext,
    RetrievalQuery,
    RetrievalResult,
)
from core.retrieval_engine.policies import ExecutionPolicy
from core.retrieval_planner.models import RetrievalPlan


class IRetrievalEngine(ABC):
    @abstractmethod
    async def execute(
        self,
        plan: RetrievalPlan,
        policy: ExecutionPolicy | None = None,
    ) -> RetrievalResult: ...


class IRetriever(ABC):
    @property
    @abstractmethod
    def retriever_id(self) -> str: ...

    @property
    @abstractmethod
    def supported_strategy(self) -> str: ...

    @property
    def sequential_only(self) -> bool:
        return False

    @property
    def experimental(self) -> bool:
        return False

    @abstractmethod
    async def retrieve(
        self,
        query: RetrievalQuery,
        context: RetrievalContext,
    ) -> list[RawCandidate]: ...


class IQueryExpander(ABC):
    @property
    @abstractmethod
    def expander_id(self) -> str: ...

    @property
    @abstractmethod
    def expansion_type(self) -> str: ...

    @abstractmethod
    def expand(self, context: ExpansionContext) -> ExpansionResult: ...


class IScoreFuser(ABC):
    @property
    @abstractmethod
    def fuser_id(self) -> str: ...

    @abstractmethod
    def fuse(
        self,
        ranked_lists: list[list[RawCandidate]],
    ) -> list[RawCandidate]: ...


class IReranker(ABC):
    @property
    @abstractmethod
    def reranker_id(self) -> str: ...

    @abstractmethod
    async def rerank(
        self,
        query_text: str,
        candidates: list[RawCandidate],
    ) -> list[RawCandidate]: ...
