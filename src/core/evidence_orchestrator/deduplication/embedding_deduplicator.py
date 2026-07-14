"""Deduplicate stage — exact and near-duplicate merging."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from core.evidence_orchestrator.config import EvidenceOrchestratorConfig
from core.evidence_orchestrator.interfaces import IDeduplicator
from core.evidence_orchestrator.models import CollectedItem, DedupMethod, EvidenceItemSource
from core.evidence_orchestrator.text_similarity import (
    char_ngrams,
    cosine_similarity,
    jaccard_similarity,
)

if TYPE_CHECKING:
    from core.evidence_orchestrator.interfaces import IEmbeddingProvider

logger = logging.getLogger(__name__)


class EmbeddingDeduplicator(IDeduplicator):
    def __init__(
        self,
        embedding_provider: IEmbeddingProvider | None = None,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._last_method_used: DedupMethod = "exact_only"

    @property
    def last_method_used(self) -> DedupMethod:
        return self._last_method_used

    async def deduplicate(
        self,
        items: list[CollectedItem],
        config: EvidenceOrchestratorConfig,
    ) -> list[CollectedItem]:
        started = time.perf_counter()
        if not items:
            self._last_method_used = "exact_only"
            return []

        survivors = list(items)
        if config.dedup_exact_enabled:
            survivors = _exact_dedup(survivors)

        merged_count = len(items) - len(survivors)
        method: DedupMethod = "exact_only"

        if config.dedup_near_enabled and len(survivors) > 1:
            if len(survivors) > config.dedup_near_batch_limit:
                method = "character_ngram"
                logger.warning(
                    "near_dedup batch limit exceeded count=%d limit=%d; "
                    "using character n-gram fallback",
                    len(survivors),
                    config.dedup_near_batch_limit,
                )
                before = len(survivors)
                survivors = _near_dedup_ngram(
                    survivors, threshold=config.dedup_similarity_threshold
                )
                merged_count += before - len(survivors)
            elif self._embedding_provider is not None:
                try:
                    method = "embedding"
                    before = len(survivors)
                    survivors = await _near_dedup_embedding(
                        survivors,
                        provider=self._embedding_provider,
                        threshold=config.dedup_similarity_threshold,
                    )
                    merged_count += before - len(survivors)
                except Exception as exc:  # noqa: BLE001
                    method = "character_ngram"
                    logger.warning(
                        "embedding near-dedup failed error=%s; "
                        "falling back to character n-gram",
                        exc,
                    )
                    before = len(survivors)
                    survivors = _near_dedup_ngram(
                        survivors, threshold=config.dedup_similarity_threshold
                    )
                    merged_count += before - len(survivors)
            else:
                method = "character_ngram"
                before = len(survivors)
                survivors = _near_dedup_ngram(
                    survivors, threshold=config.dedup_similarity_threshold
                )
                merged_count += before - len(survivors)

        self._last_method_used = method
        latency_ms = (time.perf_counter() - started) * 1000.0
        logger.info(
            "stage=deduplicate input_count=%d output_count=%d "
            "duplicates_merged=%d method_used=%s latency_ms=%.2f",
            len(items),
            len(survivors),
            merged_count,
            method,
            latency_ms,
        )
        return survivors


def _exact_dedup(items: list[CollectedItem]) -> list[CollectedItem]:
    by_chunk: dict[str, CollectedItem] = {}
    order: list[str] = []
    for item in items:
        key = item.candidate.chunk_id
        if key not in by_chunk:
            by_chunk[key] = item
            order.append(key)
        else:
            by_chunk[key] = _merge_collected(by_chunk[key], item)
    return [by_chunk[k] for k in order]


def _merge_collected(a: CollectedItem, b: CollectedItem) -> CollectedItem:
    winner, loser = (a, b) if a.candidate.score >= b.candidate.score else (b, a)
    merged_score = max(a.candidate.score, b.candidate.score)
    sources = _union_sources(winner.contributing_sources, loser.contributing_sources)
    new_candidate = winner.candidate.model_copy(update={"score": merged_score})
    return winner.model_copy(
        update={
            "candidate": new_candidate,
            "contributing_sources": sources,
            "strategy_id": winner.strategy_id,
        }
    )


def _union_sources(
    left: list[EvidenceItemSource],
    right: list[EvidenceItemSource],
) -> list[EvidenceItemSource]:
    seen: dict[str, EvidenceItemSource] = {}
    for source in left + right:
        existing = seen.get(source.strategy_id)
        if existing is None or source.raw_score > existing.raw_score:
            seen[source.strategy_id] = source
    return list(seen.values())


async def _near_dedup_embedding(
    items: list[CollectedItem],
    *,
    provider: IEmbeddingProvider,
    threshold: float,
) -> list[CollectedItem]:
    texts = [item.effective_text for item in items]
    vectors = await provider.embed_texts(texts)
    merged = [False] * len(items)
    survivors: list[CollectedItem] = []

    for i in range(len(items)):
        if merged[i]:
            continue
        current = items[i]
        for j in range(i + 1, len(items)):
            if merged[j]:
                continue
            sim = cosine_similarity(vectors[i], vectors[j])
            if sim >= threshold:
                current = _merge_collected(current, items[j])
                merged[j] = True
        survivors.append(current)
    return survivors


def _near_dedup_ngram(
    items: list[CollectedItem],
    *,
    threshold: float,
) -> list[CollectedItem]:
    ngrams = [char_ngrams(item.effective_text) for item in items]
    merged = [False] * len(items)
    survivors: list[CollectedItem] = []

    for i in range(len(items)):
        if merged[i]:
            continue
        current = items[i]
        for j in range(i + 1, len(items)):
            if merged[j]:
                continue
            sim = jaccard_similarity(ngrams[i], ngrams[j])
            if sim >= threshold:
                current = _merge_collected(current, items[j])
                merged[j] = True
        survivors.append(current)
    return survivors
