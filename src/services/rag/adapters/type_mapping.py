"""Centralized type mapping between legacy RetrievedDocument and engine RawCandidate."""

from __future__ import annotations

from typing import Any

from core.evidence_orchestrator.models import CollectedItem, EvidenceItemSource
from core.retrieval_engine.models import RawCandidate, RetrievedCandidate, SourceRef
from models.db_schemes import RetrievedDocument


def retrieved_document_to_raw_candidate(
    doc: RetrievedDocument,
    *,
    retriever_id: str = "legacy",
    strategy: str = "semantic",
    expander_variant_id: str = "primary",
) -> RawCandidate:
    meta = doc.metadata or {}
    chunk_id = str(meta.get("chunk_id") or meta.get("id") or meta.get("record_id") or "")
    document_id = str(
        meta.get("document_id")
        or meta.get("asset_id")
        or meta.get("source_document_id")
        or chunk_id
        or "unknown"
    )
    if not chunk_id:
        chunk_id = document_id
    section_title = None
    for key in ("section", "section_title", "field_name"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            section_title = value.strip()
            break
    source_ref = SourceRef(
        document_id=document_id,
        chunk_id=chunk_id,
        page_number=meta.get("page_number") if isinstance(meta.get("page_number"), int) else None,
        section_title=section_title,
        chunk_index=meta.get("chunk_index") if isinstance(meta.get("chunk_index"), int) else None,
        document_title=meta.get("document_title") if isinstance(meta.get("document_title"), str) else None,
    )
    return RawCandidate(
        chunk_id=chunk_id,
        document_id=document_id,
        raw_score=float(doc.score if doc.score is not None else 0.0),
        retriever_id=retriever_id,
        strategy=strategy,
        expander_variant_id=expander_variant_id,
        content_excerpt=doc.text or "",
        source_ref=source_ref,
    )


def raw_candidate_to_retrieved_document(candidate: RawCandidate) -> RetrievedDocument:
    metadata: dict[str, Any] = {
        "chunk_id": candidate.chunk_id,
        "document_id": candidate.document_id,
        "retriever_id": candidate.retriever_id,
        "strategy": candidate.strategy,
        "expander_variant_id": candidate.expander_variant_id,
    }
    if candidate.source_ref is not None:
        ref = candidate.source_ref
        metadata.update(
            {
                "page_number": ref.page_number,
                "section_title": ref.section_title,
                "chunk_index": ref.chunk_index,
                "document_title": ref.document_title,
                "asset_id": ref.document_id,
            }
        )
    return RetrievedDocument(
        text=candidate.content_excerpt or "",
        score=float(candidate.raw_score),
        metadata=metadata,
    )


def raw_candidates_to_evidence_items(
    candidates: list[RawCandidate],
    *,
    strategy_id: str | None = None,
) -> list[CollectedItem]:
    """Map RawCandidates into CollectedItem intermediates used by evidence collect."""
    items: list[CollectedItem] = []
    for rank, candidate in enumerate(candidates, start=1):
        sid = strategy_id or candidate.strategy
        retrieved = RetrievedCandidate(
            chunk_id=candidate.chunk_id,
            document_id=candidate.document_id,
            score=float(candidate.raw_score),
            score_source="raw",
            source_ref=candidate.source_ref,
            content_excerpt=candidate.content_excerpt or "",
            rank=rank,
        )
        items.append(
            CollectedItem(
                candidate=retrieved,
                strategy_id=sid,
                raw_token_count=max(1, len((candidate.content_excerpt or "").split())),
                contributing_sources=[
                    EvidenceItemSource(strategy_id=sid, raw_score=float(candidate.raw_score))
                ],
                text=candidate.content_excerpt or None,
            )
        )
    return items
