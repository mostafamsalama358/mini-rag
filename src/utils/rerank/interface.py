"""Abstract interface for cross-encoder rerankers (N1).

All providers must implement ``rerank()``.  The method receives the retrieved
documents already deduplicated and ranked by RRF, and must return them in a
new order (best first) according to the cross-encoder's relevance scores.

The interface is kept minimal so new backends (bge-reranker, Voyage, etc.)
are easy to add without touching the call sites.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from models.db_schemes import RetrievedDocument


class RerankerInterface(ABC):
    """Base class for cross-encoder rerankers."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: list[RetrievedDocument],
    ) -> list[RetrievedDocument]:
        """Return *documents* sorted by cross-encoder relevance (best first).

        Parameters
        ----------
        query:
            The original user query string.
        documents:
            Candidate documents from the retrieval + RRF stage.

        Returns
        -------
        list[RetrievedDocument]
            Same documents in a new order; scores may be updated to reflect
            the cross-encoder's output.
        """
        ...
