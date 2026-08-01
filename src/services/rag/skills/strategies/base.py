"""Retrieval strategy plugin protocol (022)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RetrievalStrategy(Protocol):
    """Strategy resolved from SkillExecutionContext — not Skill/field names."""

    @property
    def name(self) -> str:
        """Registry key (e.g. ``default``, ``pair_lookup``)."""

    async def retrieve(
        self, *, ctx: Any, **kwargs: Any
    ) -> tuple[list, str]:
        """Return (documents, retrieval_path_label)."""
