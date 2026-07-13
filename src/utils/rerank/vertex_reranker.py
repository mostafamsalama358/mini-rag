"""Vertex AI Ranking API reranker.

Uses Google Cloud Discovery Engine's ``RankServiceClient.rank()`` to
cross-encoder re-score candidate documents.  Supports Arabic and English
out of the box (25+ languages, 1024 tokens per record, model version 004).

Configuration (via .env / environment):
    RAG_ENABLE_RERANKER=true
    RAG_RERANKER_BACKEND=vertex
    VERTEX_PROJECT_ID=<your-gcp-project>
    VERTEX_LOCATION=us-central1
    RAG_RERANKER_MODEL=semantic-ranker-available@latest   # optional
    RAG_RERANKER_TOP_N=5                                   # optional
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from models.db_schemes import RetrievedDocument
from .interface import RerankerInterface

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "semantic-ranker-available@latest"
# Discovery Engine Ranking API: 1024 tokens max per record.
_MAX_CHARS = 6000  # safe char budget (Arabic/English ~4 chars/token)


class VertexReranker(RerankerInterface):
    """Cross-encoder reranker backed by Vertex AI Ranking API.

    Parameters
    ----------
    project_id:
        Google Cloud project ID.
    location:
        Vertex AI location (e.g. ``"us-central1"``).
    model:
        Ranking model ID.  Defaults to ``semantic-ranker-available@latest``.
    top_n:
        Maximum number of results to return after reranking.  If ``None``
        all input documents are returned (re-ordered).
    max_chars:
        Maximum characters per document record sent to the API.
    max_retries:
        Number of retries on transient errors (quota / 503).
    retry_wait:
        Seconds to wait between retries.
    """

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model: str = _DEFAULT_MODEL,
        top_n: Optional[int] = None,
        *,
        max_chars: int = _MAX_CHARS,
        max_retries: int = 3,
        retry_wait: float = 1.0,
    ):
        self.project_id = project_id
        self.location = location
        self.model = model or _DEFAULT_MODEL
        self.top_n = top_n
        self.max_chars = max_chars
        self.max_retries = max_retries
        self.retry_wait = retry_wait

        self._client = None
        try:
            from google.cloud.discoveryengine_v1 import RankServiceClient
            self._client = RankServiceClient()
        except ImportError:
            logger.warning(
                "google-cloud-discoveryengine package not installed; "
                "VertexReranker will be a no-op. Install it with: "
                "pip install google-cloud-discoveryengine"
            )

    def _prepare_text(self, text: str | None) -> str:
        prepared = (text or "").strip()
        if self.max_chars > 0:
            return prepared[: self.max_chars]
        return prepared

    async def warmup(self) -> None:
        """Run a single dummy rank call so the first user request stays fast."""
        if not self._client:
            return
        warmup_started = time.perf_counter()
        try:
            from google.cloud.discoveryengine_v1 import RankingRecord

            dummy_records = [RankingRecord(id="warmup", content="warmup")]
            request = self._build_request("warmup", dummy_records, top_n=1)
            # Run sync client in a thread.
            await asyncio.to_thread(self._client.rank, request)
            elapsed = time.perf_counter() - warmup_started
            logger.info("Vertex reranker warmup completed in %.2fs", elapsed)
        except Exception as exc:
            elapsed = time.perf_counter() - warmup_started
            logger.warning(
                "Vertex reranker warmup failed after %.2fs: %s", elapsed, exc
            )

    def _build_request(self, query: str, records, top_n: int):
        """Build a RankRequest protobuf.

        ``ranking_config`` is a **string** resource path (not a protobuf
        object).  ``model`` and ``top_n`` are fields on ``RankRequest`` itself.
        """
        from google.cloud.discoveryengine_v1 import RankRequest

        ranking_config_path = (
            f"projects/{self.project_id}"
            f"/locations/{self.location}"
            f"/collections/default_collection"
            f"/rankingConfigs/default_ranking_config"
        )

        return RankRequest(
            ranking_config=ranking_config_path,
            model=self.model,
            top_n=top_n,
            query=query,
            records=records,
        )

    async def rerank(
        self,
        query: str,
        documents: list[RetrievedDocument],
    ) -> list[RetrievedDocument]:
        """Rerank *documents* for *query* using the Vertex AI Ranking API.

        Falls back to the original order if:
        - The discoveryengine package is not installed.
        - The API call fails for any reason (network, quota, etc.).
        - The document list is empty or has only one item.
        """
        if not documents:
            return documents

        if len(documents) == 1:
            return documents

        if self._client is None:
            return documents

        top_n = self.top_n or len(documents)

        try:
            reranked = await self._rank_with_retry(
                query=query,
                documents=documents,
                top_n=top_n,
            )
            return reranked if reranked else documents
        except Exception as exc:
            logger.warning(
                "VertexReranker.rerank() failed, returning original order: %s", exc
            )
            return documents

    async def _rank_with_retry(
        self,
        query: str,
        documents: list[RetrievedDocument],
        top_n: int,
    ) -> list[RetrievedDocument] | None:
        """Call the ranking API with retry logic."""
        from google.cloud.discoveryengine_v1 import RankingRecord

        records = [
            RankingRecord(
                id=str(idx),
                content=self._prepare_text(doc.text),
            )
            for idx, doc in enumerate(documents)
        ]
        request = self._build_request(query, records, top_n=top_n)

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await asyncio.to_thread(
                    self._client.rank, request
                )
                return self._parse_response(response, documents, top_n)
            except Exception as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    logger.warning(
                        "Vertex rerank attempt %s/%s failed: %s — retrying in %.1fs",
                        attempt + 1,
                        self.max_retries + 1,
                        exc,
                        self.retry_wait,
                    )
                    await asyncio.sleep(self.retry_wait)

        raise last_exc  # type: ignore[misc]

    @staticmethod
    def _parse_response(
        response,
        documents: list[RetrievedDocument],
        top_n: int,
    ) -> list[RetrievedDocument]:
        """Map the API response back to ``RetrievedDocument`` objects."""
        reranked: list[RetrievedDocument] = []
        results = getattr(response, "results", None) or []
        for result in results:
            record_id = getattr(result, "id", None)
            relevance_score = float(getattr(result, "relevance_score", 0.0))
            if record_id is not None:
                idx = int(record_id)
                if 0 <= idx < len(documents):
                    original = documents[idx]
                    reranked.append(
                        RetrievedDocument(
                            text=original.text,
                            score=relevance_score,
                            metadata=original.metadata,
                        )
                    )
        return reranked if reranked else documents[:top_n]
