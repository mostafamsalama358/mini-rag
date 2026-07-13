"""core/retrieval/engine.py — DEPRECATED thin re-export.

The retrieval algorithms were split into `fusion.py`, `focus.py`, and
`patterns.py` (003 refactor Phase 4a). This module re-exports every public
name so existing `from core.retrieval.engine import X` imports keep working.

Phase 5 deletes this shim once all callers import from `core.retrieval`.
"""
from .fusion import (  # noqa: F401
    deduplicate_retrieved_documents,
    hybrid_rrf,
    merge_retrieved_documents,
    rerank_retrieved_documents,
)
from .focus import (  # noqa: F401
    build_comparison_expansion_queries,
    build_retrieval_expansion_queries,
    build_section_expansion_queries,
    continuation_chunk_key,
    focus_document_text_for_query,
    is_comparison_query,
    is_detail_query,
    is_narrow_factual_query,
    needs_continuation_chunk,
    retrieval_limit_for_query,
    should_focus_document_text,
    sort_documents_for_prompt,
    split_numbered_segments,
)
from .patterns import (  # noqa: F401
    normalize_arabic_for_match,
    starts_with_other_article,
    _source_key,
)
