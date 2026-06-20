import re
import unicodedata

from models.db_schemes import RetrievedDocument
from utils.structural_split import (
    build_structural_expansion_queries,
    extract_structural_targets,
    is_structural_reference_query,
    text_references_article,
    text_references_chapter,
    is_exhaustive_list_query,
)

_AR_CHAR = r"\u0600-\u06ff\u0750-\u077f"
_AR_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u0640]")
_PERSIAN_TO_ASCII = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
_ARABIC_TO_ASCII = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
_OCR_LATIN = str.maketrans({
    "i": "ي", "I": "ي",
    "o": "و", "O": "و",
    "a": "ا", "A": "ا",
    "e": "ه", "E": "ه",
    "r": "ر", "R": "ر",
})

_ALEF = r"[اأأإآٱ]"
_YA = r"[يىi]"
_TA = r"[ةه]"

# Generic signals that the user wants lists, steps, or detailed answers (any domain).
_DETAIL_PATTERNS = [
    re.compile(
        r"\b(criteria|rules|procedures|requirements|list|items|steps|conditions|details|features|benefits|components)\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(معايير|قواعد|{_ALEF}?جراءات|شروط|فئات|تفاصيل|قائمة|خطوات|مزايا|عناصر)\b",
    ),
    re.compile(rf"(ما\s+(?:هي|هى)|اذكر|عدد|list|enumerate)", re.IGNORECASE),
    re.compile(rf"(?:^|\s)(?:ايه|{_ALEF}?يه|اى|{_ALEF}?ى|قول{_YA}|قولى|how|what|why)\s", re.IGNORECASE),
]

_SECTION_HEADER_TAIL = re.compile(
    rf"(?:{_ALEF}?و?ولا|ثان(?:يا|ية)|ثالث(?:{_ALEF}|{_TA})|رابع(?:{_ALEF}|{_TA})|خامس(?:{_ALEF}|{_TA})|"
    rf"first|second|third|fourth|fifth|\d+[\-\.\)])\s*:[^\n]*\s*$",
    re.IGNORECASE,
)

_QUESTION_PREFIX = re.compile(
    rf"^(?:ما\s+(?:هي|هى)|(?:ايه|{_ALEF}?يه|اى|{_ALEF}?ى)\s+(?:هي|هى)|what\s+are\s+the|tell\s+me|how|why)\s+",
    re.IGNORECASE,
)
_CONVERSATIONAL_PREFIX = re.compile(
    rf"^(?:قول{_YA}|قولى|اذكر|عدد)\s+",
    re.IGNORECASE,
)

_COMPARISON_PATTERNS = [
    re.compile(r"\bdifference\s+between\b", re.IGNORECASE),
    re.compile(r"\bcompare\b", re.IGNORECASE),
    re.compile(r"\bvs\.?\b", re.IGNORECASE),
    re.compile(
        rf"(?:ال?\s*فرق\s+بين|لفرق\s+بين|ما\s+(?:ال?\s*فرق|ال?\s*ف(?:ر|د)ق)\s+بين)",
        re.IGNORECASE,
    ),
]

_COMPARISON_SPLIT_AR = re.compile(
    rf"(?:ال?\s*فرق\s+بين|لفرق\s+بين|ما\s+(?:ال?\s*فرق|ال?\s*ف(?:ر|د)ق)\s+بين)\s+(.+?)\s+(?:و|with|and|vs\.?)\s*(.+?)(?:\?|؟|$)",
    re.IGNORECASE,
)
_COMPARISON_SPLIT_EN = re.compile(
    r"(?:difference\s+between|compare)\s+(.+?)\s+(?:and|with|vs\.?)\s*(.+?)(?:\?|$)",
    re.IGNORECASE,
)

_NARROW_FACTUAL_PATTERNS = [
    re.compile(
        r"\b(what\s+type|what\s+kind|when|which\s+table|which\s+section|formula|how\s+much|how\s+many)\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:نوع|نوعها|امتى|إمتى|متى|موعد|جدول\s+ك(?:ام|م)|في\s+(?:جدول|بند|مادة)|معاد(?:لة|له)|كم\s|أ(?:ي|ى)\s+(?:جدول|مادة|بند))",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?:^|\s)(?:ايه|{_ALEF}?يه|اى|{_ALEF}?ى)\s*(?:نوع|موعد|جدول|معاد)",
        re.IGNORECASE,
    ),
    re.compile(
        rf"نوع(?:ها|ه)?\s*(?:ايه|{_ALEF}?يه|اى|{_ALEF}?ى)",
        re.IGNORECASE,
    ),
]

_NUMBERED_SEGMENT_SPLIT = re.compile(r"(?:^|\s)(\d+)\.\s+")


def normalize_arabic_for_match(text: str) -> str:
    if not text:
        return ""

    normalized = unicodedata.normalize("NFKC", text)
    normalized = _AR_DIACRITICS.sub("", normalized)
    normalized = normalized.translate(_PERSIAN_TO_ASCII).translate(_ARABIC_TO_ASCII)
    normalized = normalized.translate(_OCR_LATIN)
    normalized = re.sub(r"[أإآٱ]", "ا", normalized)
    normalized = re.sub(r"[ىي]", "ي", normalized)
    normalized = re.sub(r"ة", "ه", normalized)
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized


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


def should_focus_document_text(query: str) -> bool:
    """Only narrow multi-section chunks for list/detail questions."""
    if is_comparison_query(query) or is_narrow_factual_query(query):
        return False
    if is_structural_reference_query(query):
        return False
    return is_detail_query(query)


def retrieval_limit_for_query(query: str, *, default_limit: int) -> int:
    if is_exhaustive_list_query(query):
        return max(default_limit, 30)
    if is_structural_reference_query(query):
        return max(default_limit, 24)
    if is_detail_query(query):
        return max(default_limit, 20)
    return default_limit


def sort_documents_for_prompt(documents: list[RetrievedDocument], query: str) -> list[RetrievedDocument]:
    if not is_structural_reference_query(query):
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


def _query_terms(query: str) -> set[str]:
    text = query or ""
    cleaned = re.sub(rf"[^\w\s{_AR_CHAR}]", " ", text)
    terms = {term for term in cleaned.split() if len(term) >= 3}

    for match in re.finditer(r"\b(\d{1,4})\b", text):
        terms.add(match.group(1))

    for match in re.finditer(r"[«\"']([^»\"']{4,})[»\"']", text):
        phrase = match.group(1).strip()
        if phrase:
            terms.add(phrase)

    return terms


def _lexical_relevance_score(text: str, query: str) -> float:
    """Normalized query-term recall in document text (0.0 to 1.0)."""
    terms = _query_terms(query)
    if not terms or not text:
        return 0.0

    normalized_text = normalize_arabic_for_match(text)
    matches = sum(
        1 for term in terms
        if normalize_arabic_for_match(term) in normalized_text
        or (term.isdigit() and term in (text or ""))
    )
    return matches / len(terms)


def _structural_relevance_boost(text: str, query: str) -> float:
    targets = extract_structural_targets(query)
    boost = 0.0

    for article_number in targets["article_numbers"]:
        if text_references_article(text, article_number):
            boost += 0.35
        elif starts_with_other_article(text, article_number):
            boost -= 0.2

    for chapter_label in targets["chapter_labels"]:
        if text_references_chapter(text, chapter_label):
            boost += 0.25

    return boost


def starts_with_other_article(text: str, article_number: str) -> bool:
    from utils.structural_split import extract_article_numbers

    numbers = extract_article_numbers(text or "")
    if not numbers:
        return False
    return numbers[0] != str(article_number) and not text_references_article(text, article_number)


def _rrf_contribution(rank: int, *, k: int) -> float:
    return 1.0 / (k + rank)


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

    match = _COMPARISON_SPLIT_AR.search(text) or _COMPARISON_SPLIT_EN.search(text)
    if not match:
        return []

    left = match.group(1).strip(" ?؟")
    right = match.group(2).strip(" ?؟")
    expansions: list[str] = []
    if left:
        expansions.append(left)
    if right and right != left:
        expansions.append(right)
    return expansions


def build_retrieval_expansion_queries(query: str) -> list[str]:
    text = (query or "").strip()
    if not text:
        return []

    seen: set[str] = set()
    expansions: list[str] = []

    for candidate in (
        *build_section_expansion_queries(text),
        *build_comparison_expansion_queries(text),
        *build_structural_expansion_queries(text),
    ):
        normalized = candidate.strip()
        if not normalized or normalized == text or normalized in seen:
            continue
        seen.add(normalized)
        expansions.append(normalized)

    return expansions


def rerank_retrieved_documents(
    documents: list[RetrievedDocument],
    query: str,
    *,
    rrf_k: int = 60,
) -> list[RetrievedDocument]:
    """Fuse vector and lexical rankings with reciprocal rank fusion (RRF)."""
    if not documents:
        return []

    vector_ranked = sorted(documents, key=lambda item: item.score, reverse=True)
    lexical_ranked = sorted(
        documents,
        key=lambda item: _lexical_relevance_score(item.text or "", query),
        reverse=True,
    )

    vector_ranks = {id(doc): rank for rank, doc in enumerate(vector_ranked, start=1)}
    lexical_ranks = {id(doc): rank for rank, doc in enumerate(lexical_ranked, start=1)}

    reranked: list[RetrievedDocument] = []
    for document in documents:
        lexical_score = _lexical_relevance_score(document.text or "", query)
        structural_boost = _structural_relevance_boost(document.text or "", query)
        combined = (
            _rrf_contribution(vector_ranks[id(document)], k=rrf_k)
            + _rrf_contribution(lexical_ranks[id(document)], k=max(1, rrf_k // 3))
        )
        reranked.append(
            RetrievedDocument(
                text=document.text,
                score=combined + lexical_score * 1e-4 + structural_boost * 1e-3,
                metadata=document.metadata,
            )
        )

    return sorted(
        reranked,
        key=lambda item: (
            item.score,
            _lexical_relevance_score(item.text or "", query),
            _structural_relevance_boost(item.text or "", query),
        ),
        reverse=True,
    )


def merge_retrieved_documents(
    *document_groups: list[RetrievedDocument],
) -> list[RetrievedDocument]:
    combined: list[RetrievedDocument] = []
    for group in document_groups:
        combined.extend(group or [])
    return combined


def _source_key(metadata: dict | None) -> str | None:
    if not metadata:
        return None

    file_name = metadata.get("file_name")
    page = metadata.get("page")
    chunk_order = metadata.get("chunk_order")

    if file_name is not None and page is not None and chunk_order is not None:
        return f"{file_name}|{page}|{chunk_order}"

    if file_name is not None and page is not None:
        return f"{file_name}|{page}"

    if file_name is not None:
        return str(file_name)

    return None


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
