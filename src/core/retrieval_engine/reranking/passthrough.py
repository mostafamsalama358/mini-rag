"""Passthrough reranker — preserves fusion ordering."""

from __future__ import annotations

from core.retrieval_engine.interfaces import IReranker
from core.retrieval_engine.models import RawCandidate


class PassthroughReranker(IReranker):
    @property
    def reranker_id(self) -> str:
        return "passthrough"

    async def rerank(
        self,
        query_text: str,
        candidates: list[RawCandidate],
    ) -> list[RawCandidate]:
        return list(candidates)
