"""Explicit semantic-parser failure types for diagnostics and retry logging."""
from __future__ import annotations


class SemanticParseJsonError(ValueError):
    """LLM output could not be turned into a ``QueryPlan``."""

    def __init__(
        self,
        category: str,
        message: str,
        *,
        raw: str | None = None,
        payload_text: str | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.raw = raw
        self.payload_text = payload_text
        if cause is not None:
            self.__cause__ = cause

    def __str__(self) -> str:
        return f"{self.category}: {super().__str__()}"
