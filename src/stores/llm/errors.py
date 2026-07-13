"""LLM provider failure types with stable diagnostic categories."""
from __future__ import annotations

from typing import Any


class VertexGenerationError(RuntimeError):
    """Vertex AI text generation failed before usable output was produced."""

    def __init__(
        self,
        category: str,
        message: str,
        *,
        diagnostics: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.diagnostics = diagnostics or {}
        if cause is not None:
            self.__cause__ = cause

    def __str__(self) -> str:
        return f"{self.category}: {super().__str__()}"
