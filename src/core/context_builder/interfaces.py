"""Context Builder pluggable interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.context_builder.config import ContextBuilderConfig
from core.context_builder.models import ConflictGroup, ContextBlock
from core.evidence_orchestrator.interfaces import ITokenCounter
from core.evidence_orchestrator.models import EvidenceItem


class ITokenBudgetAllocator(ABC):
    @abstractmethod
    def allocate(self, config: ContextBuilderConfig) -> int: ...


class IContextCompressor(ABC):
    @abstractmethod
    async def compress(
        self,
        item: EvidenceItem,
        target_tokens: int,
        token_counter: ITokenCounter,
    ) -> tuple[str, int]: ...


class IConflictDetector(ABC):
    @abstractmethod
    async def detect(
        self,
        items: list[EvidenceItem],
        config: ContextBuilderConfig,
    ) -> list[ConflictGroup]: ...


class IContextStitcher(ABC):
    @abstractmethod
    async def stitch(
        self,
        items: list[tuple[EvidenceItem, str, bool]],
        token_counter: ITokenCounter,
    ) -> list[ContextBlock]: ...
