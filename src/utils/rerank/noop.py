"""No-op reranker — returns documents in their original order.

Used as the default when ``RAG_ENABLE_RERANKER=false`` or no backend is
configured. Keeps the call site in RAGService/NLPController unconditional:
it always calls ``reranker.rerank()``, and the no-op provider makes that a
free pass-through.
"""

from __future__ import annotations

from models.db_schemes import RetrievedDocument
from .interface import RerankerInterface


class NoOpReranker(RerankerInterface):
    """Identity reranker: returns documents unchanged."""

    async def rerank(
        self,
        query: str,
        documents: list[RetrievedDocument],
    ) -> list[RetrievedDocument]:
        return documents
