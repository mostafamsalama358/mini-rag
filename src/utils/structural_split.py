import re

_AR_ORDINAL = (
    r"(?:ال)?(?:"
    r"اول|اولى|أول|أولى|"
    r"ثاني|ثانية|ثان|"
    r"ثالث|ثالثة|"
    r"رابع|رابعة|"
    r"خامس|خامسة|"
    r"سادس|سادسة|"
    r"سابع|سابعة|"
    r"ثامن|ثامنة|"
    r"تاسع|تاسعة|"
    r"عاشر|عاشرة|"
    r"\d+"
    r")"
)

# Split before chapter/section/article headers (generic, multilingual).
_STRUCTURAL_BOUNDARY = re.compile(
    rf"(?="
    rf"(?:الفصل|الباب|القسم)\s+{_AR_ORDINAL}\b|"
    rf"(?:chapter|section|part|article)\s+\d+\b|"
    rf"(?:\(\s*)?م[ـ]?ادة\s*\(?\s*\d+"
    rf")",
    re.IGNORECASE,
)

_ARTICLE_NUMBER = re.compile(
    r"(?:\(\s*)?م[ـ]?ادة\s*\(?\s*(\d+)",
    re.IGNORECASE,
)

_CHAPTER_HEADER = re.compile(
    rf"(?:الفصل|الباب|القسم)\s+({_AR_ORDINAL})",
    re.IGNORECASE,
)

_CHAPTER_QUERY = re.compile(
    rf"(?:ال?\s*(?:فصل|باب|قسم)|chapter|section|part)\s+(?:رقم\s+)?({_AR_ORDINAL})",
    re.IGNORECASE,
)

_ARTICLE_QUERY = re.compile(
    rf"(?:ال?\s*م[ـ]?ادة|article)\s*(?:رقم\s*)?\(?\s*(\d+)",
    re.IGNORECASE,
)

_EN_ARTICLE_QUERY = re.compile(
    r"\barticle\s+(\d+)\b",
    re.IGNORECASE,
)


def split_at_structural_boundaries(text: str, *, min_segment_chars: int = 80) -> list[str]:
    """Split long text at generic chapter/section/article headers."""
    stripped = (text or "").strip()
    if not stripped:
        return []
    if len(stripped) <= min_segment_chars:
        return [stripped]

    parts = _STRUCTURAL_BOUNDARY.split(stripped)
    segments = [part.strip() for part in parts if part and part.strip()]
    if len(segments) <= 1:
        return [stripped]

    merged: list[str] = []
    buffer = ""
    for segment in segments:
        if not buffer:
            buffer = segment
            continue
        if len(buffer) < min_segment_chars and not _STRUCTURAL_BOUNDARY.search(segment):
            buffer = f"{buffer}\n{segment}"
            continue
        merged.append(buffer)
        buffer = segment
    if buffer:
        merged.append(buffer)

    return merged if len(merged) > 1 else [stripped]


def extract_article_numbers(text: str) -> list[str]:
    return list(dict.fromkeys(match.group(1) for match in _ARTICLE_NUMBER.finditer(text or "")))


def extract_structural_targets(query: str) -> dict:
    text = (query or "").strip()
    article_numbers: list[str] = []
    chapter_labels: list[str] = []

    for pattern in (_ARTICLE_QUERY, _EN_ARTICLE_QUERY):
        for match in pattern.finditer(text):
            article_numbers.append(match.group(1))

    for match in _CHAPTER_QUERY.finditer(text):
        chapter_labels.append(match.group(1).strip())

    for match in re.finditer(r"\b(\d{1,3})\b", text):
        if "مادة" in text or "article" in text.lower():
            article_numbers.append(match.group(1))

    return {
        "article_numbers": list(dict.fromkeys(article_numbers)),
        "chapter_labels": list(dict.fromkeys(chapter_labels)),
    }


def is_structural_reference_query(query: str) -> bool:
    targets = extract_structural_targets(query)
    return bool(targets["article_numbers"] or targets["chapter_labels"])


def text_references_article(text: str, article_number: str) -> bool:
    if not text or not article_number:
        return False
    normalized = re.sub(r"\s+", "", text)
    patterns = [
        rf"م[ـ]?ادة\s*\(?\s*{re.escape(article_number)}\b",
        rf"م[ـ]?ادة{re.escape(article_number)}\b",
        rf"\(\s*م[ـ]?ادة\s*{re.escape(article_number)}\s*:",
    ]
    return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in patterns)


def text_references_chapter(text: str, chapter_label: str) -> bool:
    if not text or not chapter_label:
        return False
    label = chapter_label.strip()
    patterns = [
        rf"(?:الفصل|الباب|القسم)\s+{re.escape(label)}\b",
        rf"(?:chapter|section|part)\s+{re.escape(label)}\b",
    ]
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def starts_different_article(text: str, article_number: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False

    head = stripped[:220]
    numbers = extract_article_numbers(head)
    if not numbers:
        return False
    return numbers[0] != str(article_number)


def starts_different_chapter(text: str, chapter_label: str) -> bool:
    if not text or not chapter_label:
        return False
    target = chapter_label.strip()
    head = (text or "").strip()[:220]
    for match in _CHAPTER_HEADER.finditer(head):
        found = match.group(1).strip()
        if found and found != target:
            return True
    return False


def article_context_limit(query: str) -> int:
    if is_exhaustive_list_query(query):
        return 18
    return 12


def is_exhaustive_list_query(query: str) -> bool:
    text = (query or "").strip()
    if not text:
        return False

    patterns = [
        re.compile(rf"(?:اذكر|عدد|list|enumerate)\s+(?:كل\s+)?(?:شروط|بنود|عناصر|items|conditions|requirements)", re.IGNORECASE),
        re.compile(rf"(?:كل\s+)?(?:شروط|بنود|عناصر)\s+(?:ال?\s*م[ـ]?ادة|article)", re.IGNORECASE),
        re.compile(r"\b(?:all|every)\b.*\b(?:conditions|requirements|items|criteria)\b", re.IGNORECASE),
    ]
    return any(pattern.search(text) for pattern in patterns)


def find_article_anchor_index(chunks, article_number: str) -> int | None:
    sorted_chunks = sorted(chunks, key=lambda item: item.chunk_order)
    fallback: int | None = None

    for index, chunk in enumerate(sorted_chunks):
        text = chunk.chunk_text or ""
        if not text_references_article(text, article_number):
            continue

        numbers = extract_article_numbers(text)
        if numbers and numbers[0] == str(article_number):
            return index

        if fallback is None:
            fallback = index

    return fallback


def collect_article_context_chunks(chunks, article_number: str, *, max_chunks: int = 12):
    sorted_chunks = sorted(chunks, key=lambda item: item.chunk_order)
    anchor_index = find_article_anchor_index(sorted_chunks, article_number)
    if anchor_index is None:
        return []

    selected = [sorted_chunks[anchor_index]]
    for chunk in sorted_chunks[anchor_index + 1:]:
        if starts_different_article(chunk.chunk_text or "", article_number):
            break
        selected.append(chunk)
        if len(selected) >= max_chunks:
            break

    return selected


def build_structural_expansion_queries(query: str) -> list[str]:
    targets = extract_structural_targets(query)
    expansions: list[str] = []

    for number in targets["article_numbers"]:
        expansions.append(f"مادة {number}")
        expansions.append(f"( مادة{number}")

    for label in targets["chapter_labels"]:
        expansions.append(f"الفصل {label}")

    return expansions
