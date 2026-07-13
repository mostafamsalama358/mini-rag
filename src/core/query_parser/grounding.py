"""Catalog entity grounding — deterministic fingerprint match."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Iterable

from .schema import QueryPlan

_ARABIC_TOKEN_RE = re.compile(r"[\u0600-\u06FF]{3,}")
_LATIN_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]{2,}")
_ARABIC_ENTITY_STOPWORDS = frozenset({
    "ايه", "اية", "يه", "كل", "جميع", "ما", "هل", "عن", "في", "من",
    "تركيز", "تركيزات", "جرعة", "جرعات", "تعارض", "تعارضات", "دواء",
    "استخدامات", "استخدام", "اسم", "هي", "هو", "ماهي", "ماهو",
    "سعر", "سعره", "شركة", "شركته", "فئة", "فئته", "تصنيف", "تصنيفه",
})


def _normalize_arabic_entity_token(token: str) -> str:
    """Strip the definite article so ``الدواء`` matches stopword ``دواء``."""
    t = (token or "").strip()
    if t.startswith("ال") and len(t) > 3:
        return t[2:]
    return t


def phonetic_fingerprint(text: str) -> str:
    s = (text or "").lower()
    for src, dst in (("ph", "f"), ("kh", "k"), ("sh", "s"), ("th", "t"), ("gh", "g")):
        s = s.replace(src, dst)
    s = "".join(char for char in s if char.isalpha())
    s = (
        s.replace("k", "c")
        .replace("q", "c")
        .replace("p", "b")
        .replace("v", "f")
        .replace("y", "i")
        .replace("w", "o")
    )
    return "".join(char for char in s if char not in "aeiou")


def build_catalog_fingerprint_index(
    catalog_terms: Iterable[str],
    *,
    min_fingerprint_length: int = 3,
) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for term in catalog_terms or []:
        brand = (term or "").strip()
        if not brand:
            continue
        first = brand.split()[0]
        fingerprint = phonetic_fingerprint(first)
        if len(fingerprint) < min_fingerprint_length:
            continue
        bucket = index.setdefault(fingerprint, [])
        upper = first.upper()
        if not any(existing.upper() == upper for existing in bucket):
            bucket.append(first)
    return index


def _transliterate_arabic(token: str) -> str:
    mapping = {
        "ا": "a", "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h",
        "خ": "kh", "د": "d", "ذ": "dh", "ر": "r", "ز": "z", "س": "s",
        "ش": "sh", "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "ع": "a",
        "غ": "gh", "ف": "f", "ق": "q", "ك": "k", "ل": "l", "م": "m",
        "ن": "n", "ه": "h", "و": "w", "ي": "y", "ى": "a", "ة": "a",
        "ئ": "y", "ؤ": "w", "ء": "a",
    }
    return "".join(mapping.get(ch, ch) for ch in token)


def _resolve_entity_alias(
    entity: str,
    aliases: dict[str, str] | None,
) -> tuple[str | None, float]:
    needle = (entity or "").strip()
    if not needle or not aliases:
        return None, 0.0
    needle_cf = needle.casefold()
    for alias, canonical in aliases.items():
        alias_cf = (alias or "").strip().casefold()
        if not alias_cf:
            continue
        if needle_cf == alias_cf or alias_cf in needle_cf or needle_cf in alias_cf:
            return canonical, 1.0
    return None, 0.0


def _best_catalog_match(
    entity: str,
    catalog_terms: list[str],
    fingerprint_index: dict[str, list[str]] | None,
    *,
    min_score: float,
    entity_aliases: dict[str, str] | None = None,
) -> tuple[str | None, float]:
    needle = (entity or "").strip()
    if not needle:
        return None, 0.0

    aliased, alias_score = _resolve_entity_alias(needle, entity_aliases)
    if aliased:
        return aliased, alias_score

    for term in catalog_terms:
        first = term.strip().split()[0]
        if first.upper() == needle.upper():
            return first, 1.0

    for term in catalog_terms:
        if needle in term or term in needle:
            return term.strip().split()[0], 0.95

    for term in catalog_terms:
        first = term.strip().split()[0]
        if needle.upper() in term.upper() or term.upper() in needle.upper():
            return first, 0.95

    index = fingerprint_index or build_catalog_fingerprint_index(catalog_terms)
    if not index:
        return None, 0.0

    tokens = _ARABIC_TOKEN_RE.findall(needle) or [needle]
    best_score = 0.0
    best_term: str | None = None

    for token in tokens:
        latin = _transliterate_arabic(token)
        fingerprint = phonetic_fingerprint(latin)
        candidates = index.get(fingerprint, [])
        for brand in candidates:
            brand_norm = brand.lower().replace("-", "").replace(" ", "")
            ratio = SequenceMatcher(None, latin, brand_norm).ratio()
            if ratio > best_score:
                best_score = ratio
                best_term = brand

        for brand in catalog_terms:
            first = brand.strip().split()[0]
            brand_fp = phonetic_fingerprint(first)
            if len(brand_fp) >= 3 and (
                fingerprint.startswith(brand_fp) or brand_fp.startswith(fingerprint)
            ):
                ratio = 0.88
            else:
                ratio = SequenceMatcher(None, fingerprint, brand_fp).ratio()
            if ratio > best_score:
                best_score = ratio
                best_term = first

    if best_score >= min_score:
        return best_term, best_score
    return None, best_score


def infer_entity_from_query(
    query: str,
    catalog_terms: list[str] | None,
    fingerprint_index: dict[str, list[str]] | None = None,
    *,
    min_score: float = 0.55,
    entity_aliases: dict[str, str] | None = None,
) -> tuple[str | None, float]:
    """Best-effort catalog match from raw query text (no LLM)."""
    terms = list(catalog_terms or [])
    if not terms or not (query or "").strip():
        return None, 0.0

    index = fingerprint_index or build_catalog_fingerprint_index(terms)
    # Latin brand tokens are explicit catalog names — try them before Arabic
    # question words (e.g. "استخدامات" was fuzzy-matching unrelated brands).
    latin_tokens = _LATIN_TOKEN_RE.findall(query)
    arabic_tokens = sorted(
        [
            token for token in _ARABIC_TOKEN_RE.findall(query)
            if _normalize_arabic_entity_token(token) not in _ARABIC_ENTITY_STOPWORDS
        ],
        key=len,
        reverse=True,
    )
    tokens = latin_tokens + arabic_tokens

    best_entity: str | None = None
    best_score = 0.0
    for token in tokens:
        aliased, alias_score = _resolve_entity_alias(token, entity_aliases)
        if aliased and alias_score > best_score:
            best_score = alias_score
            best_entity = aliased
            if alias_score >= 1.0:
                return aliased, alias_score
            continue
        matched, score = _best_catalog_match(
            token,
            terms,
            index,
            min_score=min_score,
            entity_aliases=entity_aliases,
        )
        if score > best_score:
            best_score = score
            best_entity = matched
        if matched and score >= 0.95:
            return matched, score

    if best_entity:
        return best_entity, best_score
    return None, best_score


def ground_entity(
    plan: QueryPlan,
    catalog_terms: list[str] | None,
    fingerprint_index: dict[str, list[str]] | None = None,
    *,
    min_score: float = 0.82,
    enabled: bool = True,
    entity_aliases: dict[str, str] | None = None,
) -> tuple[QueryPlan, float | None]:
    """Ground plan.entity against the project catalog."""
    if not enabled or plan.needs_clarification or not plan.entity:
        return plan, None

    terms = list(catalog_terms or [])
    if not terms:
        return plan, None

    aliased, alias_score = _resolve_entity_alias(plan.entity, entity_aliases)
    if aliased:
        return plan.model_copy(update={"entity": aliased, "entities": [aliased]}), alias_score

    matched, score = _best_catalog_match(
        plan.entity,
        terms,
        fingerprint_index,
        min_score=min_score,
        entity_aliases=entity_aliases,
    )
    if matched:
        grounded_entities = [matched]
        if plan.entities:
            grounded_entities = []
            for raw in plan.entities:
                g, _ = _best_catalog_match(
                    raw,
                    terms,
                    fingerprint_index,
                    min_score=min_score,
                    entity_aliases=entity_aliases,
                )
                grounded_entities.append(g or raw)
        return plan.model_copy(update={"entity": matched, "entities": grounded_entities}), score

    return plan.model_copy(
        update={
            "needs_clarification": True,
            "clarification_prompt": (
                f"I could not find '{plan.entity}' in the indexed catalog. "
                "Please check the spelling or name a specific item."
            ),
        }
    ), score
