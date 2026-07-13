"""core/retrieval/focus.py — query classification, expansion, segment focus.

Split out of `core/retrieval/engine.py` (003 refactor Phase 4a). The query
understanding side of retrieval: classifying query intent (detail/comparison/
narrow/exhaustive), building expansion sub-queries, picking the most relevant
numbered segment of a chunk, continuation-chunk detection, and prompt ordering.

Shared lexical/scoring primitives live in `patterns.py`.
"""
from __future__ import annotations

import re

from models.db_schemes import RetrievedDocument
from core.structural.engine import (
    StructuralPatterns,
    build_structural_expansion_queries,
    is_structural_reference_query,
    is_exhaustive_list_query,
)

from .patterns import (
    _COMPARISON_PATTERNS,
    _COMPARISON_SPLIT_AR,
    _COMPARISON_SPLIT_EN,
    _CONVERSATIONAL_PREFIX,
    _DETAIL_PATTERNS,
    _lexical_relevance_score,
    _NARROW_FACTUAL_PATTERNS,
    _NUMBERED_SEGMENT_SPLIT,
    _QUESTION_PREFIX,
    _SECTION_HEADER_TAIL,
    normalize_arabic_for_match,
)


def is_detail_query(query: str) -> bool:
    text = (query or "").strip()
    if not text:
        return False

    return any(pattern.search(text) for pattern in _DETAIL_PATTERNS)


def is_comparison_query(query: str) -> bool:
    text = (query or "").strip()
    if not text:
        return False

    return any(pattern.search(text) for pattern in _COMPARISON_PATTERNS)


def is_narrow_factual_query(query: str) -> bool:
    text = (query or "").strip()
    if not text:
        return False

    return any(pattern.search(text) for pattern in _NARROW_FACTUAL_PATTERNS)


def should_focus_document_text(query: str, *, structural_patterns: StructuralPatterns | None = None) -> bool:
    """Only narrow multi-section chunks for list/detail questions."""
    if is_comparison_query(query) or is_narrow_factual_query(query):
        return False
    if is_structural_reference_query(query, patterns=structural_patterns):
        return False
    return is_detail_query(query)


def retrieval_limit_for_query(query: str, *, default_limit: int, structural_patterns: StructuralPatterns | None = None) -> int:
    if is_exhaustive_list_query(query):
        return max(default_limit, 30)
    if is_structural_reference_query(query, patterns=structural_patterns):
        return max(default_limit, 24)
    if is_detail_query(query):
        return max(default_limit, 20)
    return default_limit


def sort_documents_for_prompt(documents: list[RetrievedDocument], query: str, *, structural_patterns: StructuralPatterns | None = None) -> list[RetrievedDocument]:
    if not is_structural_reference_query(query, patterns=structural_patterns):
        return documents

    def sort_key(document: RetrievedDocument):
        metadata = document.metadata or {}
        page = metadata.get("page")
        chunk_order = metadata.get("chunk_order")
        try:
            page_value = int(page)
        except (TypeError, ValueError):
            page_value = 0
        try:
            order_value = int(chunk_order)
        except (TypeError, ValueError):
            order_value = 0
        return (str(metadata.get("file_name") or ""), page_value, order_value)

    return sorted(documents, key=sort_key)


def split_numbered_segments(text: str) -> list[str]:
    stripped = (text or "").strip()
    if not stripped:
        return []

    parts = _NUMBERED_SEGMENT_SPLIT.split(stripped)
    if len(parts) < 3:
        return [stripped]

    segments: list[str] = []
    for index in range(1, len(parts), 2):
        number = parts[index]
        body = parts[index + 1].strip() if index + 1 < len(parts) else ""
        if body:
            segments.append(f"{number}. {body}")

    return segments if len(segments) >= 2 else [stripped]


def focus_document_text_for_query(text: str, query: str) -> str:
    """Pick the numbered segment with the highest query-term overlap, if any."""
    segments = split_numbered_segments(text)
    if len(segments) <= 1:
        return text or ""

    ranked = sorted(
        segments,
        key=lambda segment: _lexical_relevance_score(segment, query),
        reverse=True,
    )
    best_segment = ranked[0]
    best_score = _lexical_relevance_score(best_segment, query)
    full_score = _lexical_relevance_score(text, query)

    if best_score >= max(0.25, full_score * 0.75):
        return best_segment.strip()

    return text or ""


def build_section_expansion_queries(query: str) -> list[str]:
    text = (query or "").strip()
    if not text or not is_detail_query(text):
        return []

    expansions: list[str] = []
    stripped = _QUESTION_PREFIX.sub("", text).strip(" ?؟")
    if stripped and stripped != text:
        expansions.append(stripped)

    shorter = _CONVERSATIONAL_PREFIX.sub("", stripped or text).strip(" ?؟")
    if shorter and shorter not in expansions and shorter != text:
        expansions.append(shorter)

    return expansions


def build_comparison_expansion_queries(query: str) -> list[str]:
    text = (query or "").strip()
    if not text or not is_comparison_query(text):
        return []

    left, right = extract_comparison_terms(text)
    expansions: list[str] = []
    if left:
        expansions.append(left)
    if right and right != left:
        expansions.append(right)
    return expansions


def extract_comparison_terms(query: str) -> tuple[str | None, str | None]:
    """Return (left, right) entity phrases from a comparison question."""
    text = (query or "").strip()
    if not text:
        return None, None
    match = _COMPARISON_SPLIT_AR.search(text) or _COMPARISON_SPLIT_EN.search(text)
    if not match:
        return None, None
    left = match.group(1).strip(" ?؟")
    right = match.group(2).strip(" ?؟")
    return (left or None), (right or None)


def _document_matches_term(doc: RetrievedDocument, term: str) -> bool:
    term_u = (term or "").strip().upper()
    if not term_u:
        return False
    text_u = (doc.text or "").upper()
    if term_u in text_u:
        return True
    # Structured "fields" view (canonical, written by the chunker) plus a few
    # generic entity-style keys. No dataset-specific column names — the row's
    # text already carries every field value, so the text match above is the
    # primary signal and these keys are only a fallback for stripped metadata.
    metadata = doc.metadata or {}
    fields_view = metadata.get("fields")
    if isinstance(fields_view, dict):
        for value in fields_view.values():
            if term_u in str(value or "").upper():
                return True
    for key in ("brand_name", "trade_name", "product_name"):
        value = str(metadata.get(key) or "").upper()
        if term_u in value:
            return True
    return False


def ground_documents_to_entity(
    documents: list[RetrievedDocument],
    *,
    entity_tokens: list[str],
    related_tokens: list[str] | None = None,
    related_only: bool = False,
) -> list[RetrievedDocument]:
    """Filter *documents* down to those anchored on the committed entity.

    Pure, dataset-agnostic grounding for entity-scoped follow-ups.

    *entity_tokens* is the full set of resolved spellings of the committed
    entity (raw query token + catalog/alias-resolved Latin form + the full
    effective-entity string). A document matches the entity if ANY spelling
    appears in its text — this prevents both over-filtering (entity present
    under a normalized name) and under-filtering (a different product leaking
    in when the entity is genuinely absent).

    When *related_only* is true (related-only intents such as "alternatives"),
    documents carrying the related metadata tokens but NOT the entity are
    preferred (those are the *other* trade names); entity rows are kept as a
    secondary tier.

    This function NEVER falls back to the unfiltered input. If the entity is
    committed but no candidate mentions it, an empty list is returned so the
    caller takes the clean "no information" path instead of leaking off-entity
    rows into the prompt. Generic over every entity × every field.
    """
    entity_u = {
        (t or "").strip().upper() for t in (entity_tokens or []) if (t or "").strip()
    }
    related_u = [m.upper() for m in (related_tokens or []) if (m or "").strip()]
    if not entity_u:
        return list(documents or [])

    def _haystack_matches(doc: RetrievedDocument, tokens_u: set[str]) -> bool:
        """True if ANY token appears in the row text OR in the structured
        ``fields`` view the chunker writes (canonical values that may not be
        spelled the same in the text representation). Mirrors
        ``_document_matches_term`` so there is a single matching contract."""
        text_u = (doc.text or "").upper()
        if any(tok in text_u for tok in tokens_u):
            return True
        metadata = doc.metadata or {}
        fields_view = metadata.get("fields")
        if isinstance(fields_view, dict):
            for value in fields_view.values():
                value_u = str(value or "").upper()
                if any(tok in value_u for tok in tokens_u):
                    return True
        return False

    other_trade: list[RetrievedDocument] = []
    entity_rows: list[RetrievedDocument] = []
    for doc in documents or []:
        has_related = _haystack_matches(doc, set(related_u)) if related_u else False
        has_entity = _haystack_matches(doc, entity_u)
        if related_only and related_u:
            if has_related and not has_entity:
                other_trade.append(doc)
            elif has_related and has_entity:
                entity_rows.append(doc)
        elif has_entity or has_related:
            entity_rows.append(doc)

    if related_only and related_u:
        return other_trade or entity_rows
    return entity_rows


def prioritize_comparison_documents(
    documents: list[RetrievedDocument],
    query: str,
) -> list[RetrievedDocument]:
    """Move docs that mention compared entities ahead of generic semantic hits."""
    left, right = extract_comparison_terms(query)
    if not left or not right or not documents:
        return documents

    both: list[RetrievedDocument] = []
    left_only: list[RetrievedDocument] = []
    right_only: list[RetrievedDocument] = []
    rest: list[RetrievedDocument] = []

    for doc in documents:
        has_left = _document_matches_term(doc, left)
        has_right = _document_matches_term(doc, right)
        if has_left and has_right:
            both.append(doc)
        elif has_left:
            left_only.append(doc)
        elif has_right:
            right_only.append(doc)
        else:
            rest.append(doc)

    return both + left_only + right_only + rest


def build_retrieval_expansion_queries(query: str, *, structural_patterns: StructuralPatterns | None = None) -> list[str]:
    text = (query or "").strip()
    if not text:
        return []

    seen: set[str] = set()
    expansions: list[str] = []

    for candidate in (
        *build_section_expansion_queries(text),
        *build_comparison_expansion_queries(text),
        *build_structural_expansion_queries(text, patterns=structural_patterns),
    ):
        normalized = candidate.strip()
        if not normalized or normalized == text or normalized in seen:
            continue
        seen.add(normalized)
        expansions.append(normalized)

    return expansions


def needs_continuation_chunk(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped.endswith(":"):
        return False

    if _SECTION_HEADER_TAIL.search(stripped):
        return True

    if re.search(r"step\s+\d+\s*:", stripped, re.IGNORECASE):
        return True

    if re.search(r"(?:^|\s)\d+[\.\)]\s+[^:]+:\s*$", stripped):
        return True

    normalized = normalize_arabic_for_match(stripped)
    if re.search(r"(?:اولا|ثانيا|ثالثا|رابعا|خامس)", normalized):
        return True

    return bool(re.search(r"\b(?:first|second|third|fourth|fifth)\b", stripped, re.IGNORECASE))


def continuation_chunk_key(metadata: dict | None) -> tuple | None:
    if not metadata:
        return None

    asset_id = metadata.get("asset_id")
    chunk_order = metadata.get("chunk_order")
    if asset_id is None or chunk_order is None:
        return None

    try:
        return int(asset_id), int(chunk_order) + 1
    except (TypeError, ValueError):
        return None
