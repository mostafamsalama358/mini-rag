"""StrategyRegistry — plugin resolution only, no name branching in callers."""

from __future__ import annotations

from typing import Any

from services.rag.skills.strategies.base import RetrievalStrategy


class StrategyRegistry:
    """Register and resolve retrieval strategies by name."""

    def __init__(self) -> None:
        self._strategies: dict[str, RetrievalStrategy] = {}

    def register(self, strategy: RetrievalStrategy) -> None:
        self._strategies[strategy.name] = strategy

    def get(self, name: str) -> RetrievalStrategy:
        return self._strategies.get(name) or self._strategies["default"]

    async def execute(
        self,
        name: str,
        *,
        ctx: Any,
        **kwargs: Any,
    ) -> tuple[list, str]:
        strategy = self.get(name)
        return await strategy.retrieve(ctx=ctx, **kwargs)
