"""core/retrieval/fusion.py — rank fusion, merge, dedupe, rerank.

Split out of `core/retrieval/engine.py` (003 refactor Phase 4a). Algorithms
that combine multiple retrieval result lists into one ranked list:
Reciprocal Rank Fusion (dense+sparse), multi-group merge, source/text
deduplication, and the cross-encoder-style lexical+structural reranker.

Shared lexical/scoring primitives live in `patterns.py`.
"""
from __future__ import annotations

from models.db_schemes import RetrievedDocument
from core.structural.engine import StructuralPatterns

from .patterns import (
    _lexical_relevance_score,
    _rrf_contribution,
    _source_key,
    _structural_relevance_boost,
)


def merge_retrieved_documents(
    *document_groups: list[RetrievedDocument],
) -> list[RetrievedDocument]:
    combined: list[RetrievedDocument] = []
    for group in document_groups:
        combined.extend(group or [])
    return combined


def hybrid_rrf(
    dense_results: list[RetrievedDocument],
    sparse_results: list[RetrievedDocument],
    *,
    k: int = 60,
    limit: int = 30,
) -> list[RetrievedDocument]:
    """Classical Reciprocal Rank Fusion over independent dense and sparse rankings."""
    if not dense_results and not sparse_results:
        return []

    if not sparse_results:
        return deduplicate_retrieved_documents(dense_results, limit=limit)

    if not dense_results:
        return deduplicate_retrieved_documents(sparse_results, limit=limit)

    dense_ranks: dict[str, int] = {}
    for rank, doc in enumerate(dense_results, start=1):
        key = _source_key(doc.metadata) or (doc.text or "").strip()[:240]
        if key:
            dense_ranks[key] = rank

    sparse_ranks: dict[str, int] = {}
    for rank, doc in enumerate(sparse_results, start=1):
        key = _source_key(doc.metadata) or (doc.text or "").strip()[:240]
        if key:
            sparse_ranks[key] = rank

    all_keys = set(dense_ranks) | set(sparse_ranks)
    doc_by_key: dict[str, RetrievedDocument] = {}

    for doc in dense_results:
        key = _source_key(doc.metadata) or (doc.text or "").strip()[:240]
        if key:
            doc_by_key[key] = doc

    for doc in sparse_results:
        key = _source_key(doc.metadata) or (doc.text or "").strip()[:240]
        if key and key not in doc_by_key:
            doc_by_key[key] = doc

    rrf_scored: list[RetrievedDocument] = []
    for key in all_keys:
        dr = dense_ranks.get(key)
        sr = sparse_ranks.get(key)
        score = 0.0
        if dr is not None:
            score += 1.0 / (k + dr)
        if sr is not None:
            score += 1.0 / (k + sr)

        original = doc_by_key.get(key)
        if original is not None:
            rrf_scored.append(
                RetrievedDocument(
                    text=original.text,
                    score=score,
                    metadata=original.metadata,
                )
            )

    rrf_scored.sort(key=lambda d: d.score, reverse=True)
    return rrf_scored[:limit]


def deduplicate_retrieved_documents(
    documents: list[RetrievedDocument],
    *,
    limit: int,
) -> list[RetrievedDocument]:
    if not documents:
        return []

    seen_sources: set[str] = set()
    seen_text_prefixes: set[str] = set()
    unique: list[RetrievedDocument] = []

    for document in sorted(documents, key=lambda item: item.score, reverse=True):
        source_key = _source_key(document.metadata)
        text_prefix = (document.text or "").strip()[:240]

        if source_key and source_key in seen_sources:
            continue

        if text_prefix and text_prefix in seen_text_prefixes:
            continue

        if source_key:
            seen_sources.add(source_key)

        if text_prefix:
            seen_text_prefixes.add(text_prefix)

        unique.append(document)

        if len(unique) >= limit:
            break

    return unique


def rerank_retrieved_documents(
    documents: list[RetrievedDocument],
    query: str,
    *,
    rrf_k: int = 60,
    structural_patterns: StructuralPatterns | None = None,
) -> list[RetrievedDocument]:
    """Fuse vector and lexical rankings with reciprocal rank fusion (RRF)."""
    if not documents:
        return []

    # Pre-compute the (expensive) per-document scores once and reuse them.
    lexical_scores = [
        _lexical_relevance_score(doc.text or "", query) for doc in documents
    ]
    structural_boosts = [
        _structural_relevance_boost(doc.text or "", query, patterns=structural_patterns) for doc in documents
    ]

    vector_ranked = sorted(
        range(len(documents)), key=lambda i: documents[i].score, reverse=True
    )
    lexical_ranked = sorted(
        range(len(documents)), key=lambda i: lexical_scores[i], reverse=True
    )

    vector_ranks = {idx: rank for rank, idx in enumerate(vector_ranked, start=1)}
    lexical_ranks = {idx: rank for rank, idx in enumerate(lexical_ranked, start=1)}

    reranked: list[RetrievedDocument] = []
    for idx, document in enumerate(documents):
        combined = (
            _rrf_contribution(vector_ranks[idx], k=rrf_k)
            + _rrf_contribution(lexical_ranks[idx], k=max(1, rrf_k // 3))
        )
        reranked.append(
            RetrievedDocument(
                text=document.text,
                score=combined + lexical_scores[idx] * 1e-4 + structural_boosts[idx] * 1e-3,
                metadata=document.metadata,
            )
        )

    # Sort by precomputed scores — no recomputation in the key function.
    order = sorted(
        range(len(reranked)),
        key=lambda i: (
            reranked[i].score,
            lexical_scores[i],
            structural_boosts[i],
        ),
        reverse=True,
    )
    return [reranked[i] for i in order]
