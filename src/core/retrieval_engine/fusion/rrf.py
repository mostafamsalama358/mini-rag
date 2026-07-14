"""Reciprocal Rank Fusion score fuser."""

from __future__ import annotations

from core.retrieval_engine.interfaces import IScoreFuser
from core.retrieval_engine.models import RawCandidate


class RRFScoreFuser(IScoreFuser):
    def __init__(self, k: int = 60) -> None:
        self._k = k

    @property
    def fuser_id(self) -> str:
        return "rrf"

    def fuse(self, ranked_lists: list[list[RawCandidate]]) -> list[RawCandidate]:
        if not ranked_lists:
            return []
        if len(ranked_lists) == 1:
            return list(ranked_lists[0])

        scores: dict[str, float] = {}
        best: dict[str, RawCandidate] = {}

        for ranked in ranked_lists:
            for rank, candidate in enumerate(ranked, start=1):
                cid = candidate.chunk_id
                scores[cid] = scores.get(cid, 0.0) + 1.0 / (self._k + rank)
                existing = best.get(cid)
                if existing is None or candidate.raw_score > existing.raw_score:
                    best[cid] = candidate

        ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        fused: list[RawCandidate] = []
        for chunk_id, rrf_score in ordered:
            base = best[chunk_id]
            fused.append(
                base.model_copy(update={"raw_score": rrf_score})
            )
        return fused
