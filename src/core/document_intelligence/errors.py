"""Typed degradation signal for Document Intelligence (FR-011 / research R7)."""

from __future__ import annotations

from typing import Literal

DegradationReason = Literal["unsupported_structure", "parse_error", "empty_content"]


class DocumentIntelligenceDegraded(Exception):
    """Raised when structured parsing cannot proceed at full fidelity.

    Callers MUST catch this, build a degraded DocumentModel via
    ``build_fallback_model``, and continue ingestion. Hard file-open/read
    failures MUST NOT use this exception — they propagate as normal errors.
    """

    def __init__(
        self,
        reason: DegradationReason,
        message: str = "",
        *,
        best_effort_text: str | None = None,
    ) -> None:
        self.reason: DegradationReason = reason
        self.best_effort_text = best_effort_text
        super().__init__(message or reason)
