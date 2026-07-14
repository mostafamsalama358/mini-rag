"""Text similarity helpers for deduplication and compressibility scoring."""

from __future__ import annotations

import math


def char_ngrams(text: str, n: int = 3) -> set[str]:
    normalized = (text or "").lower()
    if not normalized:
        return set()
    if len(normalized) < n:
        return {normalized}
    return {normalized[i : i + n] for i in range(len(normalized) - n + 1)}


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))
