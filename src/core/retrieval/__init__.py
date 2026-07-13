"""core.retrieval — domain-agnostic retrieval primitives (stable package API).

The retrieval algorithms live in three focused modules (003 refactor Phase 4a):
  - fusion.py   : RRF, hybrid merge, dedupe, lexical/structural rerank
  - focus.py    : query classification, expansion, segment focus, continuation
  - patterns.py : shared lexical/scoring primitives (Arabic norm, RRF, source key)

Import from the package: `from core.retrieval import hybrid_rrf, is_detail_query`.
The legacy `core.retrieval.engine` path still works (re-exports) and is removed
in Phase 5 once all callers import from the package directly.
"""
from .fusion import (
    deduplicate_retrieved_documents,
    hybrid_rrf,
    merge_retrieved_documents,
    rerank_retrieved_documents,
)
from .focus import (
    build_comparison_expansion_queries,
    build_retrieval_expansion_queries,
    build_section_expansion_queries,
    continuation_chunk_key,
    focus_document_text_for_query,
    ground_documents_to_entity,
    is_comparison_query,
    is_detail_query,
    is_narrow_factual_query,
    needs_continuation_chunk,
    prioritize_comparison_documents,
    retrieval_limit_for_query,
    should_focus_document_text,
    sort_documents_for_prompt,
    split_numbered_segments,
)
from .patterns import (
    normalize_arabic_for_match,
    starts_with_other_article,
    _source_key,
)

__all__ = [
    # fusion
    "deduplicate_retrieved_documents",
    "hybrid_rrf",
    "merge_retrieved_documents",
    "rerank_retrieved_documents",
    # focus
    "build_comparison_expansion_queries",
    "build_retrieval_expansion_queries",
    "build_section_expansion_queries",
    "continuation_chunk_key",
    "focus_document_text_for_query",
    "ground_documents_to_entity",
    "is_comparison_query",
    "is_detail_query",
    "is_narrow_factual_query",
    "needs_continuation_chunk",
    "prioritize_comparison_documents",
    "retrieval_limit_for_query",
    "should_focus_document_text",
    "sort_documents_for_prompt",
    "split_numbered_segments",
    # patterns
    "normalize_arabic_for_match",
    "starts_with_other_article",
    "_source_key",
]
