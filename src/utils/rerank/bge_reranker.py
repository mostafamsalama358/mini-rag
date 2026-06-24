import logging
import time
from typing import Sequence
import asyncio

from models.db_schemes import RetrievedDocument
from .interface import RerankerInterface

logger = logging.getLogger(__name__)

class BgeReranker(RerankerInterface):
    """Reranks retrieved documents using BAAI's FlagReranker (BGE)."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-v2-m3",
        top_n: int | None = None,
        *,
        device: str = "cpu",
        batch_size: int = 8,
        use_fp16: bool = False,
        max_chars: int = 1024,
    ):
        self.model_name = model_name
        self.top_n = top_n
        self.device = (device or "cpu").strip()
        self.batch_size = max(1, int(batch_size or 8))
        self.use_fp16 = bool(use_fp16)
        self.max_chars = max(0, int(max_chars or 0))
        self.reranker = None
        self.load_duration_seconds = 0.0
        self.warmup_duration_seconds = 0.0
        load_started = time.perf_counter()
        try:
            from FlagEmbedding import FlagReranker
            init_kwargs = {"use_fp16": self.use_fp16}
            if self.device:
                init_kwargs["devices"] = [self.device]
            self.reranker = FlagReranker(model_name, **init_kwargs)
            self.load_duration_seconds = time.perf_counter() - load_started
            logger.info(
                "Loaded BGE Reranker model: %s on %s in %.2fs (fp16=%s, batch_size=%s)",
                model_name,
                self.device,
                self.load_duration_seconds,
                self.use_fp16,
                self.batch_size,
            )
        except ImportError:
            self.load_duration_seconds = time.perf_counter() - load_started
            logger.error("FlagEmbedding package not found. Please install FlagEmbedding.")
        except Exception as e:
            self.load_duration_seconds = time.perf_counter() - load_started
            logger.error(f"Failed to load BGE Reranker model {model_name}: {e}")

    def _prepare_text(self, text: str | None) -> str:
        prepared = (text or "").strip()
        if self.max_chars > 0:
            return prepared[:self.max_chars]
        return prepared

    async def warmup(self) -> None:
        """Run a tiny local inference once so first user traffic stays fast."""
        if not self.reranker:
            return
        warmup_started = time.perf_counter()
        try:
            await asyncio.to_thread(
                self.reranker.compute_score,
                [["warmup", "warmup"]],
                batch_size=1,
                normalize=True,
            )
            self.warmup_duration_seconds = time.perf_counter() - warmup_started
            logger.info("BGE reranker warmup completed in %.2fs", self.warmup_duration_seconds)
        except Exception as exc:
            self.warmup_duration_seconds = time.perf_counter() - warmup_started
            logger.warning("BGE reranker warmup failed after %.2fs: %s", self.warmup_duration_seconds, exc)

    async def rerank(
        self,
        query: str,
        documents: Sequence[RetrievedDocument],
    ) -> list[RetrievedDocument]:
        if not documents:
            return []

        if not self.reranker:
            logger.warning("BGE Reranker not initialized; returning original ordering.")
            return list(documents)

        pairs = [[query, self._prepare_text(doc.text)] for doc in documents]
        top_n = self.top_n or len(documents)

        try:
            scores = await asyncio.to_thread(
                self.reranker.compute_score,
                pairs,
                batch_size=self.batch_size,
                normalize=True,
            )
            
            # If there's only one pair, scores might be a float rather than a list
            if isinstance(scores, float):
                scores = [scores]

            scored_docs = []
            for doc, score in zip(documents, scores):
                scored_docs.append(
                    RetrievedDocument(
                        text=doc.text,
                        score=float(score),
                        metadata=doc.metadata,
                    )
                )

            # Sort best-first
            scored_docs.sort(key=lambda x: x.score, reverse=True)

            if self.top_n and self.top_n > 0:
                return scored_docs[:top_n]

            return scored_docs
            
        except Exception as e:
            logger.error(f"BGE reranking failed: {e}")
            return list(documents)
