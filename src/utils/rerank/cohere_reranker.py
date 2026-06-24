"""Cohere cross-encoder reranker (N1).

Uses the Cohere Rerank API (``cohere.Client.rerank`` / ``AsyncClient.rerank``)
to re-score the candidate documents and return them in cross-encoder order.

The Cohere rerank endpoint accepts a query + a list of documents and returns
relevance scores in [0, 1] from a dedicated cross-encoder model (e.g.
``rerank-multilingual-v3.0``).  Scores from the cross-encoder replace the
previous RRF fusion scores so the prompt stage always sees the most relevant
documents first.

Configuration (via .env / environment):
    RAG_ENABLE_RERANKER=true
    RAG_RERANKER_BACKEND=cohere
    COHERE_API_KEY=<your key>
    COHERE_RERANKER_MODEL=rerank-multilingual-v3.0   # optional
"""

from __future__ import annotations

import logging
from typing import Optional

from models.db_schemes import RetrievedDocument
from .interface import RerankerInterface

logger = logging.getLogger(__name__)

# Default model — works for Arabic + English (multilingual).
_DEFAULT_MODEL = "rerank-multilingual-v3.0"


class CohereReranker(RerankerInterface):
    """Cross-encoder reranker backed by Cohere's Rerank API.

    Parameters
    ----------
    api_key:
        Cohere API key.
    model:
        Rerank model ID.  Defaults to ``rerank-multilingual-v3.0``.
    top_n:
        Maximum number of results to return after reranking.  If ``None``
        all input documents are returned (re-ordered).
    """

    def __init__(
        self,
        api_key: str,
        model: str = _DEFAULT_MODEL,
        top_n: Optional[int] = None,
    ):
        self.api_key = api_key
        self.model = model or _DEFAULT_MODEL
        self.top_n = top_n

        try:
            import cohere
            # Prefer the async client when available (cohere >= 5.x).
            if hasattr(cohere, "AsyncClient"):
                self._async_client = cohere.AsyncClient(api_key=api_key)
            else:
                self._async_client = None
            self._sync_client = cohere.Client(api_key=api_key)
        except ImportError:
            logger.warning(
                "cohere package not installed; CohereReranker will be a no-op. "
                "Install it with: pip install cohere"
            )
            self._async_client = None
            self._sync_client = None

    async def rerank(
        self,
        query: str,
        documents: list[RetrievedDocument],
    ) -> list[RetrievedDocument]:
        """Rerank *documents* for *query* using the Cohere Rerank API.

        Falls back to the original order if:
        - The cohere package is not installed.
        - The API call fails for any reason (network, quota, etc.).
        - The document list is empty or has only one item.
        """
        if not documents:
            return documents

        if len(documents) == 1:
            return documents

        if self._async_client is None and self._sync_client is None:
            return documents

        doc_texts = [doc.text or "" for doc in documents]
        top_n = self.top_n or len(documents)

        try:
            if self._async_client is not None:
                response = await self._async_client.rerank(
                    query=query,
                    documents=doc_texts,
                    model=self.model,
                    top_n=top_n,
                )
            else:
                # Older cohere SDK — run sync in thread to avoid blocking.
                import asyncio
                response = await asyncio.to_thread(
                    self._sync_client.rerank,
                    query=query,
                    documents=doc_texts,
                    model=self.model,
                    top_n=top_n,
                )
        except Exception as exc:
            logger.warning(f"CohereReranker.rerank() failed, returning original order: {exc}")
            return documents

        # Build re-ordered list; update score to reflect cross-encoder judgment.
        reranked: list[RetrievedDocument] = []
        results = getattr(response, "results", None) or []
        for result in results:
            idx = result.index
            relevance_score = float(getattr(result, "relevance_score", 0.0))
            original = documents[idx]
            reranked.append(
                RetrievedDocument(
                    text=original.text,
                    score=relevance_score,
                    metadata=original.metadata,
                )
            )

        return reranked if reranked else documents
