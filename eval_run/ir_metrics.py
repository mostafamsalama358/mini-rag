"""Standard IR metrics computed from real ranked output vs hand-labeled relevance."""

from __future__ import annotations

import math


def recall_at_k(ranked_ids: list[str], relevant: set[str], k: int) -> float | None:
    if not relevant:
        return None
    top_k = set(ranked_ids[:k])
    return len(top_k & relevant) / len(relevant)


def precision_at_k(ranked_ids: list[str], relevant: set[str], k: int) -> float | None:
    if not relevant:
        return None
    top_k = ranked_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for cid in top_k if cid in relevant)
    return hits / len(top_k)


def mrr(ranked_ids: list[str], relevant: set[str]) -> float | None:
    if not relevant:
        return None
    for idx, cid in enumerate(ranked_ids, start=1):
        if cid in relevant:
            return 1.0 / idx
    return 0.0


def ndcg_at_k(ranked_ids: list[str], relevant: set[str], k: int) -> float | None:
    if not relevant:
        return None
    dcg = 0.0
    for idx, cid in enumerate(ranked_ids[:k], start=1):
        rel = 1.0 if cid in relevant else 0.0
        dcg += rel / math.log2(idx + 1)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(idx + 1) for idx in range(1, ideal_hits + 1))
    if idcg == 0:
        return 0.0
    return dcg / idcg
