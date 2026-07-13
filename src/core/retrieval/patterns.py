"""core/retrieval/patterns.py — shared lexical primitives for retrieval.

Split out of `core/retrieval/engine.py` (003 refactor Phase 4a). These are the
low-level, dependency-free helpers used by both `fusion.py` and `focus.py`:
Arabic normalization, query-term extraction, lexical/structural relevance
scoring, RRF contribution, source-key derivation, and the shared regex sets.

These contain NO domain-specific regex of their own — structural signals rely
on patterns the pipeline supplies (generic defaults kept here for backward
compat; legal/pharmacy patterns live in fields/{domain}/*.yaml).
"""
import re
import unicodedata

from models.db_schemes import RetrievedDocument
from core.structural.engine import (
    StructuralPatterns,
    extract_structural_targets,
    text_references_article,
    text_references_chapter,
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

# Generic signals that the user wants lists, steps, or detailed answers.
# These are the generic pack's intents; domain packs add their own in YAML.
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
    rf"^(?:ما\s+(?:هي|هى)|(?:ايه|{_ALEF}?يه|اى|{_ALEF}?ى)\s+(?:هي|هوى)|what\s+are\s+the|tell\s+me|how|why)\s+",
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
    normalized = re.sub(r"ة", "ه", normalized)
    normalized = re.sub(r"ى", "ي", normalized)
    normalized = re.sub(r"ؤ", "و", normalized)
    normalized = re.sub(r"ئ", "ي", normalized)
    normalized = re.sub(r"[^\w\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized


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


def _structural_relevance_boost(text: str, query: str, *, patterns: StructuralPatterns | None = None) -> float:
    targets = extract_structural_targets(query, patterns=patterns)
    boost = 0.0

    for article_number in targets["article_numbers"]:
        if text_references_article(text, article_number, patterns=patterns):
            boost += 0.35
        elif starts_with_other_article(text, article_number, patterns=patterns):
            boost -= 0.2

    for chapter_label in targets["chapter_labels"]:
        if text_references_chapter(text, chapter_label, patterns=patterns):
            boost += 0.25

    return boost


def starts_with_other_article(text: str, article_number: str, *, patterns: StructuralPatterns | None = None) -> bool:
    from core.structural.engine import extract_article_numbers

    numbers = extract_article_numbers(text or "", patterns=patterns)
    if not numbers:
        return False
    return numbers[0] != str(article_number) and not text_references_article(text, article_number, patterns=patterns)


def _rrf_contribution(rank: int, *, k: int) -> float:
    return 1.0 / (k + rank)


def _source_key(metadata: dict | None) -> str | None:
    """Stable identity for a retrieved chunk during RRF / dedupe.

    PDF/page chunks use file+page(+order). Row-chunked spreadsheets have no
    ``page`` — only ``file_name`` — so falling back to file alone collapses
    every row in an xlsx into one hit (e.g. all Panadol SKUs → one product).
    Prefer ``row_index`` / ``chunk_order`` when present.
    """
    if not metadata:
        return None

    file_name = metadata.get("file_name")
    page = metadata.get("page")
    chunk_order = metadata.get("chunk_order")
    row_index = metadata.get("row_index")

    if file_name is not None and page is not None and chunk_order is not None:
        return f"{file_name}|{page}|{chunk_order}"

    if file_name is not None and page is not None:
        return f"{file_name}|{page}"

    # Spreadsheet / row chunks (pharmacy catalogs, CSVs).
    if file_name is not None and row_index is not None:
        return f"{file_name}|row:{row_index}"

    if file_name is not None and chunk_order is not None:
        return f"{file_name}|order:{chunk_order}"

    if file_name is not None:
        return str(file_name)

    return None
