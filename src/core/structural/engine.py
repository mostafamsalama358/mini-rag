"""core/structural/engine.py — structural boundary engine (FULLY GENERIC).

This engine contains NO domain-specific patterns. All chapter/article/
boundary patterns are supplied by the caller via a compiled
`StructuralPatterns` object, which is built from a field pack's
`structural_split.yaml` (e.g. `fields/legal/structural_split.yaml`).

When no patterns are supplied (generic pack, or `patterns=None`) every
function degrades to a safe no-op:
  - `split_at_structural_boundaries` returns the whole text as one segment
  - `extract_structural_targets` returns empty targets
  - `is_structural_reference_query` returns False

This is the "generic = minimal" contract (spec 002): a generic project does
not get legal article logic, and a legal project's patterns come entirely
from its field pack YAML.

utils/structural_split.py re-exports every name below for backward compat.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass
class StructuralPatterns:
    """Compiled structural patterns derived from a field pack's YAML.

    Built by `compile_structural_patterns(profile)`. All entries are
    pre-compiled `re.Pattern` objects (or empty) for runtime speed.

    Fields:
      boundaries: patterns that match BEFORE a structural header; used to
        split long text into segments (each pattern is typically wrapped in
        a lookahead `(?=...)`).
      article_query_patterns: patterns with one capturing group — the article
        number — used to detect article references in a user query.
      chapter_query_patterns: patterns with one capturing group — the chapter
        label — used to detect chapter references in a query.
      article_text_patterns: patterns with one capturing group matching an
        article number in a chunk's body text.
      chapter_text_patterns: patterns matching a chapter header in body text.
      article_reference_prefix / article_reference_suffix: how to wrap an
        article number when testing whether a chunk references it (e.g. the
        Arabic "مادة" prefix). Both may be empty for Latin domains.
      expansion_article_template / expansion_chapter_template: format strings
        (with `{value}`) for building retrieval expansion queries.
    """

    boundaries: list[re.Pattern] = field(default_factory=list)
    article_query_patterns: list[re.Pattern] = field(default_factory=list)
    chapter_query_patterns: list[re.Pattern] = field(default_factory=list)
    article_text_patterns: list[re.Pattern] = field(default_factory=list)
    chapter_text_patterns: list[re.Pattern] = field(default_factory=list)
    # Wrap article numbers when testing body-text references.
    article_reference_prefix: str = ""
    article_reference_suffix: str = ""
    # Templates for expansion-query construction (contain {value}).
    expansion_article_template: str = "{value}"
    expansion_chapter_template: str = "{value}"
    # When True, a bare number near an article keyword is also accepted.
    bare_number_article_hint_keywords: list[str] = field(default_factory=list)


def _compile_all(patterns: Iterable[str], flags: int = re.IGNORECASE) -> list[re.Pattern]:
    compiled: list[re.Pattern] = []
    for raw in patterns or []:
        if not raw:
            continue
        try:
            compiled.append(re.compile(raw, flags))
        except re.error:
            continue
    return compiled


def compile_structural_patterns(profile_or_dict: Any) -> StructuralPatterns:
    """Build a `StructuralPatterns` from a StructuralProfile (or raw dict).

    Reads the keys declared in `fields/{domain}/structural_split.yaml`.
    Generic packs supply an empty/minimal profile → empty patterns → no-op.
    """
    if profile_or_dict is None:
        return StructuralPatterns()

    # Accept either a Pydantic StructuralProfile or a plain dict.
    if hasattr(profile_or_dict, "model_dump"):
        data = profile_or_dict.model_dump()
    elif isinstance(profile_or_dict, dict):
        data = profile_or_dict
    else:
        return StructuralPatterns()

    return StructuralPatterns(
        boundaries=_compile_all(data.get("boundaries") or []),
        article_query_patterns=_compile_all(data.get("article_query_patterns") or []),
        chapter_query_patterns=_compile_all(data.get("chapter_query_patterns") or []),
        article_text_patterns=_compile_all(data.get("article_text_patterns") or data.get("article_query_patterns") or []),
        chapter_text_patterns=_compile_all(data.get("chapter_text_patterns") or data.get("chapter_query_patterns") or []),
        article_reference_prefix=data.get("article_reference_prefix") or "",
        article_reference_suffix=data.get("article_reference_suffix") or "",
        expansion_article_template=data.get("expansion_article_template") or "{value}",
        expansion_chapter_template=data.get("expansion_chapter_template") or "{value}",
        bare_number_article_hint_keywords=list(data.get("bare_number_article_hint_keywords") or []),
    )


# ---- engine primitives (all pattern-driven) ----

def split_at_structural_boundaries(
    text: str,
    *,
    min_segment_chars: int = 80,
    patterns: StructuralPatterns | None = None,
) -> list[str]:
    """Split long text at structural headers declared by the field pack.

    With `patterns=None` or empty boundaries → returns `[text]` (no split),
    which is the correct generic/minimal behavior.
    """
    stripped = (text or "").strip()
    if not stripped:
        return []
    if len(stripped) <= min_segment_chars:
        return [stripped]
    if patterns is None or not patterns.boundaries:
        return [stripped]

    def _is_boundary(value: str) -> bool:
        return any(p.search(value) for p in patterns.boundaries)

    # Combine all boundary patterns into a single alternation split.
    combined = re.compile("|".join(f"(?:{p.pattern})" for p in patterns.boundaries), re.IGNORECASE)
    parts = combined.split(stripped)
    segments = [part.strip() for part in parts if part and part.strip()]
    if len(segments) <= 1:
        return [stripped]

    merged: list[str] = []
    buffer = ""
    for segment in segments:
        if not buffer:
            buffer = segment
            continue
        if len(buffer) < min_segment_chars and not _is_boundary(segment):
            buffer = f"{buffer}\n{segment}"
            continue
        merged.append(buffer)
        buffer = segment
    if buffer:
        merged.append(buffer)

    return merged if len(merged) > 1 else [stripped]


def extract_article_numbers(
    text: str,
    *,
    patterns: StructuralPatterns | None = None,
) -> list[str]:
    """Extract article numbers from text using the field pack's patterns."""
    if patterns is None or not patterns.article_text_patterns:
        return []
    numbers: list[str] = []
    for compiled in patterns.article_text_patterns:
        for match in compiled.finditer(text or ""):
            if match.groups():
                numbers.append(match.group(1))
    return list(dict.fromkeys(numbers))


def extract_structural_targets(
    query: str,
    *,
    patterns: StructuralPatterns | None = None,
) -> dict:
    """Extract article numbers + chapter labels referenced in a query."""
    if patterns is None:
        return {"article_numbers": [], "chapter_labels": []}

    text = (query or "").strip()
    article_numbers: list[str] = []
    chapter_labels: list[str] = []

    for compiled in patterns.article_query_patterns:
        for match in compiled.finditer(text):
            if match.groups():
                article_numbers.append(match.group(1))

    for compiled in patterns.chapter_query_patterns:
        for match in compiled.finditer(text):
            if match.groups():
                chapter_labels.append(match.group(1).strip())

    # Optional bare-number heuristic: a number near an article keyword.
    if patterns.bare_number_article_hint_keywords:
        lowered = text.lower()
        if any(kw in lowered for kw in patterns.bare_number_article_hint_keywords):
            for match in re.finditer(r"\b(\d{1,3})\b", text):
                article_numbers.append(match.group(1))

    return {
        "article_numbers": list(dict.fromkeys(article_numbers)),
        "chapter_labels": list(dict.fromkeys(chapter_labels)),
    }


def is_structural_reference_query(
    query: str,
    *,
    patterns: StructuralPatterns | None = None,
) -> bool:
    targets = extract_structural_targets(query, patterns=patterns)
    return bool(targets["article_numbers"] or targets["chapter_labels"])


def text_references_article(
    text: str,
    article_number: str,
    *,
    patterns: StructuralPatterns | None = None,
) -> bool:
    """Test whether body text references a given article number.

    Uses the field pack's reference prefix/suffix (e.g. the Arabic "مادة"
    prefix for legal). Falls back to a bare number match when no prefix
    is configured (Latin domains).
    """
    if not text or not article_number:
        return False
    number = str(article_number)
    normalized = re.sub(r"\s+", "", text)

    prefix = (patterns.article_reference_prefix if patterns else "") or ""
    suffix = (patterns.article_reference_suffix if patterns else "") or ""
    esc_num = re.escape(number)
    candidates: list[str] = []
    if prefix:
        candidates.append(rf"{re.escape(prefix)}\s*\(?\s*{esc_num}\b")
        candidates.append(rf"{re.escape(prefix)}{esc_num}\b")
        candidates.append(rf"\(\s*{re.escape(prefix)}\s*{esc_num}\s*:")
    if suffix:
        candidates.append(rf"{esc_num}\s*\(?\s*{re.escape(suffix)}\b")
    if not candidates:
        # No domain prefix/suffix → plain word-boundary number match.
        candidates.append(rf"\b{esc_num}\b")

    return any(re.search(p, normalized, re.IGNORECASE) for p in candidates)


def text_references_chapter(
    text: str,
    chapter_label: str,
    *,
    patterns: StructuralPatterns | None = None,
) -> bool:
    """Test whether body text references a given chapter label."""
    if not text or not chapter_label:
        return False
    label = chapter_label.strip()
    if not label:
        return False
    if patterns is None or not patterns.chapter_text_patterns:
        return label in text
    esc_label = re.escape(label)
    for compiled in patterns.chapter_text_patterns:
        # Substitute the captured-group slot with the concrete label.
        pattern = compiled.pattern.replace(r"(.+)", esc_label).replace(r"(.+?)", esc_label)
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def starts_different_article(
    text: str,
    article_number: str,
    *,
    patterns: StructuralPatterns | None = None,
) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    head = stripped[:220]
    numbers = extract_article_numbers(head, patterns=patterns)
    if not numbers:
        return False
    return numbers[0] != str(article_number)


def starts_different_chapter(
    text: str,
    chapter_label: str,
    *,
    patterns: StructuralPatterns | None = None,
) -> bool:
    if not text or not chapter_label:
        return False
    target = chapter_label.strip()
    if not target or patterns is None or not patterns.chapter_text_patterns:
        return False
    head = (text or "").strip()[:220]
    return text_references_chapter(head, target, patterns=patterns) and target not in _first_chapter_label(head, patterns)


def _first_chapter_label(text: str, patterns: StructuralPatterns) -> str | None:
    for compiled in patterns.chapter_text_patterns:
        for match in compiled.finditer(text or ""):
            if match.groups():
                return match.group(1).strip()
    return None


def find_article_anchor_index(
    chunks,
    article_number: str,
    *,
    patterns: StructuralPatterns | None = None,
) -> int | None:
    sorted_chunks = sorted(chunks, key=lambda item: item.chunk_order)
    fallback: int | None = None

    for index, chunk in enumerate(sorted_chunks):
        text = chunk.chunk_text or ""
        if not text_references_article(text, article_number, patterns=patterns):
            continue
        numbers = extract_article_numbers(text, patterns=patterns)
        if numbers and numbers[0] == str(article_number):
            return index
        if fallback is None:
            fallback = index
    return fallback


def collect_article_context_chunks(
    chunks,
    article_number: str,
    *,
    max_chunks: int = 12,
    patterns: StructuralPatterns | None = None,
):
    sorted_chunks = sorted(chunks, key=lambda item: item.chunk_order)
    anchor_index = find_article_anchor_index(sorted_chunks, article_number, patterns=patterns)
    if anchor_index is None:
        return []

    selected = [sorted_chunks[anchor_index]]
    for chunk in sorted_chunks[anchor_index + 1:]:
        if starts_different_article(chunk.chunk_text or "", article_number, patterns=patterns):
            break
        selected.append(chunk)
        if len(selected) >= max_chunks:
            break
    return selected


def build_structural_expansion_queries(
    query: str,
    *,
    patterns: StructuralPatterns | None = None,
) -> list[str]:
    """Build retrieval expansion queries for structural references.

    Uses the field pack's expansion templates (e.g. legal: "مادة {value}").
    """
    targets = extract_structural_targets(query, patterns=patterns)
    expansions: list[str] = []
    article_tpl = (patterns.expansion_article_template if patterns else None) or "{value}"
    chapter_tpl = (patterns.expansion_chapter_template if patterns else None) or "{value}"

    for number in targets["article_numbers"]:
        expansions.append(article_tpl.format(value=number))
    for label in targets["chapter_labels"]:
        expansions.append(chapter_tpl.format(value=label))
    return expansions


# ---- backward-compat wrappers (DEPRECATED) ----
# These call the generic functions with no patterns → generic/minimal behavior.
# Existing utils/structural_split.py shim re-exports them. New code should pass
# an explicit `patterns=` from the active FieldProfile.

def article_context_limit(query: str, *, exhaustive: bool = False) -> int:  # pragma: no cover
    return 18 if exhaustive else 12


def is_exhaustive_list_query(query: str) -> bool:
    """Generic exhaustive-list signal (cross-domain, language-level).

    Kept in core because it's a generic retrieval-language heuristic (shared
    by all domains): "list all conditions", "اذكر الشروط". Domain-specific
    exhaustive intents (e.g. legal "شروط المادة") live in each pack's
    retrieval.yaml wide_retrieval_intents — surfaced via QueryPlan in the
    semantic parser path, or is_exhaustive_list_query for raw search API.
    """
    text = (query or "").strip()
    if not text:
        return False
    patterns = [
        re.compile(r"(?:اذكر|عدد|list|enumerate)\s+(?:كل\s+)?(?:شروط|بنود|عناصر|items|conditions|requirements)", re.IGNORECASE),
        re.compile(r"\b(?:all|every)\b.*\b(?:conditions|requirements|items|criteria)\b", re.IGNORECASE),
    ]
    return any(pattern.search(text) for pattern in patterns)
