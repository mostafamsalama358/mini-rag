"""Default token budget allocator."""

from __future__ import annotations

from core.context_builder.config import ContextBuilderConfig
from core.context_builder.interfaces import ITokenBudgetAllocator


class DefaultTokenBudgetAllocator(ITokenBudgetAllocator):
    def allocate(self, config: ContextBuilderConfig) -> int:
        return max(0, config.available_budget)
