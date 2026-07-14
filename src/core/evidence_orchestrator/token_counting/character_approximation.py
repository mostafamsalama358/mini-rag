"""Character-based token approximation counter."""

from __future__ import annotations

import math

from core.evidence_orchestrator.interfaces import ITokenCounter


class CharacterApproximationTokenCounter(ITokenCounter):
    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, math.ceil(len(text) / 4.0))
