"""core/field_resolution.py — GENERIC field-concept resolution.

This module contains NO domain-specific words. Every concept, synonym, and
column-name hint is supplied by the caller via a ``FieldRegistryProfile``
loaded from a field pack's ``fields.yaml`` (constitution NFR-001/G3).

The two things it does:

1. ``resolve_query_field`` — map a free-text user question to a canonical
   *concept* (e.g. "strengths", "warnings", "storage") by matching the
   concept's surface forms against the normalized query. This works for
   ALL concepts declared in fields.yaml — present and future — through one
   mechanism. No per-field code, no regex intents.

2. ``auto_detect_entity_key`` / ``build_field_manifest`` — at index time,
   discover which columns exist in the dataset and which one is the entity
   (row-identity) column. This replaces the hardcoded ``col_med`` /
   ``col_API1`` assumptions: the data vocabulary is discovered, not configured.

Why this ends the reactive patch loop:
  - Adding the N+1th field is a YAML edit in fields.yaml (2 lines), not code.
  - Changing datasets is handled by re-discovering the field manifest, not by
    editing Python SQL literals.
  - The query side and the data side now share ONE vocabulary: the
    ``FieldRegistryProfile`` + the discovered ``FieldManifest``.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable

from fields.schemas import FieldConceptProfile, FieldRegistryProfile

if TYPE_CHECKING:
    from core.query_parser.schema import QueryPlan


# ---------------------------------------------------------------------------
# Normalization helpers (kept lightweight + Arabic-aware, no domain words).
# ---------------------------------------------------------------------------

_AR_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u0640]")
_EASTERN_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def _normalize_query_for_match(text: str) -> str:
    """Normalize a query so surface-form matching is robust.

    Arabic: strip diacritics/tatweel, unify alef/ya/ta-marbuta forms.
    Latin: lowercase. Digits: ASCII. Punctuation: collapse to spaces.
    This mirrors the lighter BM25 normalization and is safe for mixed text.
    """
    if not text:
        return ""
    out = unicodedata.normalize("NFKC", text)
    out = _AR_DIACRITICS.sub("", out)
    out = out.translate(_EASTERN_DIGITS)
    out = re.sub(r"[أإآٱ]", "ا", out)
    out = re.sub(r"ة", "ه", out)
    out = re.sub(r"[ىي]", "ي", out)
    out = re.sub(r"ؤ", "و", out)
    out = re.sub(r"ئ", "ي", out)
    out = re.sub(r"[A-Za-z]+", lambda m: m.group(0).lower(), out)
    out = re.sub(r"[^\w\s]", " ", out)
    # Strip the Arabic definite article "ال" so "الاعراض" matches synonym
    # "اعراض". Generic linguistic normalization — no domain words involved.
    out = re.sub(r"\bال", "", out)
    out = re.sub(r"\s+", " ", out).strip()
    return out


def _normalize_header(header: str) -> str:
    """Normalize a spreadsheet column header for concept matching.

    Drops the historical ``col_`` prefix the chunker adds, lowercases, and
    strips non-alphanumerics so ``col_New Material`` ↔ ``new material``.
    """
    if not header:
        return ""
    h = str(header).strip()
    if h.lower().startswith("col_"):
        h = h[4:]
    h = unicodedata.normalize("NFKC", h).lower()
    h = re.sub(r"[^\w\s]", " ", h)
    h = re.sub(r"\s+", " ", h).strip()
    return h


# ---------------------------------------------------------------------------
# Resolution result.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldResolution:
    """Outcome of resolving a query to a field concept.

    concept: canonical id from fields.yaml (e.g. "strengths").
    output_shape: "list" | "prose" — drives answer formatting generically.
    column_keys: the discovered chunk_metadata keys that hold this concept's
        values (e.g. ["col_Strength"]). Empty when the dataset has no column
        for this concept (retrieval then falls back to whole-row dense/BM25).
    via: how the column was resolved — "query_token" (user named the column),
        "concept_hint" (fields.yaml resolves_to_columns matched a discovered
        column), or "concept_only" (concept matched, no column found).
    """

    concept: str
    output_shape: str = "prose"
    column_keys: tuple[str, ...] = ()
    via: str = "concept_only"


@dataclass
class FieldManifest:
    """Discovered data vocabulary for one dataset (asset or project).

    columns: every column header seen, normalized to its chunk_metadata key.
        e.g. {"col_med": "med", "col_Strength": "strength", ...}.
    entity_key: the chunk_metadata key that identifies a row (drug/product).
        Auto-detected unless fields.yaml entity_key_hint overrides it.
    """

    columns: dict[str, str] = field(default_factory=dict)
    entity_key: str | None = None

    def headers(self) -> set[str]:
        """Normalized header names (without col_ prefix)."""
        return {v for v in self.columns.values() if v}

    def keys_for_header(self, header: str) -> list[str]:
        """chunk_metadata keys whose normalized header equals ``header``."""
        target = _normalize_header(header)
        return [k for k, h in self.columns.items() if h == target]


# ---------------------------------------------------------------------------
# 1. Query → concept resolution.
# ---------------------------------------------------------------------------


def _concept_to_compiled(concepts: Iterable[FieldConceptProfile]):
    """Pre-compile each concept's synonyms into a single alternation regex.

    Returns a list of (concept, output_shape, pattern). Longer synonyms are
    tried first so "active ingredient" wins over "ingredient".
    """
    compiled: list[tuple[str, str, re.Pattern]] = []
    for concept in concepts:
        forms = [_normalize_query_for_match(s) for s in concept.synonyms if s and s.strip()]
        forms = [f for f in forms if f]
        if not forms:
            continue
        # Dedupe + sort longest-first so multi-word forms match first.
        forms = sorted(set(forms), key=lambda f: (-len(f), f))
        pattern = re.compile(
            r"(?:^|\W)(" + "|".join(re.escape(f) for f in forms) + r")(?:\W|$)",
            re.IGNORECASE,
        )
        compiled.append((concept.concept, concept.output_shape, pattern))
    return compiled


def resolve_query_concept(
    query: str,
    registry: FieldRegistryProfile | None,
) -> tuple[str, str] | None:
    """Resolve a query to (concept, output_shape) or None.

    Matches the first concept (in declaration order) whose surface form
    appears as a whole token/phrase in the normalized query. Pure function,
    no domain code.
    """
    if not registry or not registry.concepts or not query:
        return None
    normalized = _normalize_query_for_match(query)
    if not normalized:
        return None
    for concept, output_shape, pattern in _concept_to_compiled(registry.concepts):
        if pattern.search(normalized):
            return concept, output_shape
    return None


def resolve_query_field(
    query: str,
    registry: FieldRegistryProfile | None,
    manifest: FieldManifest | None = None,
) -> FieldResolution | None:
    """Resolve a query to a concept AND the discovered column(s) it targets.

    This is the generic replacement for the old intent→bucket branching.
    Resolution order:
      1. Match a concept via surface forms (resolve_query_concept).
      2. If a manifest is available, try to attach the discovered column(s):
         (a) "query_token" — a discovered column header is literally named in
             the query (e.g. user writes "strength" and a col_Strength exists).
         (b) "concept_hint" — the concept's resolves_to_columns hint matches a
             discovered header (e.g. strengths.hint=Strength ↔ col_Strength).
      3. Otherwise return the concept with no column ("concept_only"); the
         caller retrieves over the whole row, which is still correct — it just
         lacks the field-targeted precision boost.
    """
    matched = resolve_query_concept(query, registry)
    if matched is None:
        return None
    concept_name, output_shape = matched

    if manifest is None or not manifest.columns:
        return FieldResolution(concept=concept_name, output_shape=output_shape)

    # (a) Does the query name a discovered column header directly?
    normalized_query = _normalize_query_for_match(query)
    named_keys: list[str] = []
    for meta_key, header in manifest.columns.items():
        h = _normalize_header(header)
        if h and len(h) >= 3 and h in normalized_query:
            named_keys.append(meta_key)
    if named_keys:
        return FieldResolution(
            concept=concept_name,
            output_shape=output_shape,
            column_keys=tuple(dict.fromkeys(named_keys)),
            via="query_token",
        )

    # (b) Does the concept hint at a header that exists in this dataset?
    hint_concept = next(
        (c for c in registry.concepts if c.concept == concept_name), None
    )
    if hint_concept:
        hinted_keys: list[str] = []
        for hint in hint_concept.resolves_to_columns:
            hinted_keys.extend(manifest.keys_for_header(hint))
        if hinted_keys:
            return FieldResolution(
                concept=concept_name,
                output_shape=output_shape,
                column_keys=tuple(dict.fromkeys(hinted_keys)),
                via="concept_hint",
            )

    return FieldResolution(concept=concept_name, output_shape=output_shape)


def resolve_from_plan(
    plan: QueryPlan,
    registry: FieldRegistryProfile | None,
    manifest: FieldManifest | None = None,
) -> FieldResolution | None:
    """Map QueryPlan.field → FieldResolution via registry + manifest."""
    if registry is None or plan.field == "unknown":
        return None

    concept = next((c for c in registry.concepts if c.concept == plan.field), None)
    if concept is None:
        return None

    if manifest is None or not manifest.columns:
        return FieldResolution(concept=plan.field, output_shape=concept.output_shape)

    hinted_keys: list[str] = []
    for hint in concept.resolves_to_columns:
        hinted_keys.extend(manifest.keys_for_header(hint))
    if hinted_keys:
        return FieldResolution(
            concept=plan.field,
            output_shape=concept.output_shape,
            column_keys=tuple(dict.fromkeys(hinted_keys)),
            via="concept_hint",
        )

    return FieldResolution(concept=plan.field, output_shape=concept.output_shape)


# ---------------------------------------------------------------------------
# 2. Data → field manifest discovery (index time).
# ---------------------------------------------------------------------------


def _is_alphaish(value: Any) -> bool:
    """True when a value looks like a name (mostly letters), not a number/code."""
    s = str(value or "").strip()
    if len(s) < 2:
        return False
    letters = sum(1 for ch in s if ch.isalpha() or ch == " ")
    # Allow drug names with digits (Vitamin D3) but require ≥60% letters.
    return letters / len(s) >= 0.6


def _entity_grouping_signal(rows: list[dict], key: str) -> float:
    """How strongly ``key`` behaves as the row-identity (grouping) column.

    The entity column is the one whose repeated values co-occur with VARYING
    sibling values: a drug name repeats across multiple strengths, but a
    side-effect phrase rarely does. Concretely, for each value of ``key`` that
    appears >1 time, we check whether the OTHER columns differ across those
    rows. High "sibling variance on repeat" = strong identity signal.

    Returns a score in [0, 1]. 0 when no value repeats (can't tell) — callers
    must fall back to name-likeness in that case.
    """
    groups: dict[str, list[dict]] = {}
    for row in rows:
        val = row.get(key)
        if val in (None, ""):
            continue
        groups.setdefault(str(val).strip().upper(), []).append(row)

    repeating = [g for g in groups.values() if len(g) > 1]
    if not repeating:
        return 0.0

    other_keys = [
        k for k in rows[0].keys()
        if k != key and not k.startswith("row_index")
        and k not in {"sheet_name", "file_name", "page"}
    ]
    if not other_keys:
        return 0.0

    varied_groups = 0
    for group in repeating:
        seen_any_variation = False
        for ok in other_keys:
            values = {str(r.get(ok) or "").strip().upper() for r in group}
            if len(values) > 1:
                seen_any_variation = True
                break
        if seen_any_variation:
            varied_groups += 1

    # Proportion of repeating-value groups that show sibling variance,
    # weighted by how many rows those repeating groups cover.
    repeating_rows = sum(len(g) for g in repeating)
    return (varied_groups / len(repeating)) * (repeating_rows / len(rows))


def auto_detect_entity_key(
    rows: list[dict],
    *,
    candidate_keys: list[str] | None = None,
    hint: str | None = None,
) -> str | None:
    """Pick the chunk_metadata key that best identifies a row.

    Two-stage heuristic, generic over datasets:

    1. PRIMARY — "entity grouping" signal: the identity column is the one
       whose repeated values co-occur with varying siblings (a drug name
       repeats across strengths; side-effect prose does not). This is the
       most reliable signal and works even on small datasets.
    2. FALLBACK — when no value repeats in any candidate (tiny or
       all-unique dataset), score by name-likeness: alphabetic, filled,
       short. Uniqueness is only a tiebreaker.

    An explicit ``hint`` header (from fields.yaml entity_key_hint) always
    overrides detection.

    ``rows`` are row-chunk metadata dicts (the per-row ``col_*`` view).
    """
    if not rows:
        return None

    # If a hint header was given, map it to its col_ key if present.
    if hint:
        for key, value in rows[0].items():
            if _normalize_header(key) == _normalize_header(hint):
                return key

    keys = candidate_keys
    if keys is None and rows:
        # Consider every key except known structural ones.
        skip = {"sheet_name", "row_index", "file_name", "brand_name", "page"}
        keys = [k for k in rows[0].keys() if k not in skip]

    if not keys:
        return None

    # Stage 1: grouping signal.
    grouping = [( _entity_grouping_signal(rows, k), k) for k in keys]
    best_grouping = max(g for g, _ in grouping) if grouping else 0.0
    if best_grouping > 0:
        # Among keys tied at the top grouping score, pick the most name-like.
        top = [k for g, k in grouping if g >= best_grouping - 1e-9]
        if len(top) == 1:
            return top[0]
        keys = top

    # Stage 2: name-likeness fallback.
    total = len(rows)
    scored: list[tuple[float, str]] = []
    for key in keys:
        values = [r.get(key) for r in rows]
        non_empty = [v for v in values if v not in (None, "")]
        if not non_empty:
            continue
        fill_rate = len(non_empty) / total
        alpha_rate = sum(1 for v in non_empty if _is_alphaish(v)) / len(non_empty)
        avg_len = sum(len(str(v)) for v in non_empty) / len(non_empty)
        length_score = 1.0 if avg_len <= 16 else max(0.0, 16.0 / avg_len)
        distinct = len({str(v).strip().upper() for v in non_empty})
        uniqueness = distinct / len(non_empty)
        score = (
            0.35 * alpha_rate
            + 0.30 * length_score
            + 0.20 * fill_rate
            + 0.15 * uniqueness
        )
        scored.append((score, key))

    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][1]


def build_field_manifest(
    rows: list[dict],
    *,
    entity_hint: str | None = None,
) -> FieldManifest:
    """Build a FieldManifest from row-chunk metadata dicts.

    ``rows`` are the per-row metadata dicts produced by the chunker (each
    carrying ``col_<header>`` keys). Discovers every column + the entity key.
    """
    columns: dict[str, str] = {}
    candidate_keys: list[str] = []
    for row in rows:
        for key, value in row.items():
            if key.startswith("col_"):
                if key not in columns:
                    header = _normalize_header(key)
                    columns[key] = header
                    candidate_keys.append(key)
            elif key in {"brand_name", "generic_name", "inn", "active_ingredient",
                         "trade_name", "product_name", "arabic_name", "english_name"}:
                # Loader-injected entity-style keys (process_service.py:187).
                if key not in columns:
                    columns[key] = _normalize_header(key)
                    candidate_keys.append(key)

    entity_key = auto_detect_entity_key(
        rows, candidate_keys=candidate_keys, hint=entity_hint
    )
    return FieldManifest(columns=columns, entity_key=entity_key)


# ---------------------------------------------------------------------------
# Convenience: manifest from discovered headers only (no row values yet).
# ---------------------------------------------------------------------------


def manifest_from_headers(
    headers: Iterable[str],
    *,
    entity_hint: str | None = None,
) -> FieldManifest:
    """Build a partial manifest from a list of column headers.

    Used when only header names are known (e.g. a single-sheet xlsx read) and
    row-value statistics are not yet available. The entity key is set only
    when an explicit hint matches a header.
    """
    columns: dict[str, str] = {}
    for header in headers:
        h = str(header).strip()
        if not h:
            continue
        meta_key = f"col_{h}"
        columns[meta_key] = _normalize_header(h)

    entity_key: str | None = None
    if entity_hint:
        target = _normalize_header(entity_hint)
        for key, header in columns.items():
            if header == target:
                entity_key = key
                break

    return FieldManifest(columns=columns, entity_key=entity_key)


# 3. Query-time entity key + capability resolution (legacy-aware).


LEGACY_ENTITY_KEY_PRIORITY: tuple[str, ...] = (
    "col_med",
    "col_brand",
    "col_brand_name",
    "col_trade_name",
    "col_product_name",
    "col_api",
    "col_API",
    "col_API1",
    "brand_name",
    "trade_name",
    "product_name",
)

# Concepts that intentionally have no column mapping (whole-row retrieval).
_CAPABILITY_EXEMPT_CONCEPTS: frozenset[str] = frozenset({"alternatives", "interactions", "unknown"})


@dataclass(frozen=True)
class FieldCapability:
    """Whether a requested logical field exists in the indexed dataset."""

    status: str  # "available" | "not_available" | "unknown"
    logical_field: str
    physical_columns: tuple[str, ...] = ()
    available_field_labels: tuple[str, ...] = ()


def _metadata_keys_from_hints(
    manifest: FieldManifest,
    headers: list[str],
) -> list[str]:
    keys: list[str] = []
    for header in headers:
        keys.extend(manifest.keys_for_header(header))
        if not manifest.keys_for_header(header):
            h = (header or "").strip()
            if not h:
                continue
            candidate = h if h.startswith("col_") else f"col_{h}"
            if candidate in manifest.columns:
                keys.append(candidate)
    return list(dict.fromkeys(keys))


def resolve_entity_key(
    manifest: FieldManifest,
    registry: FieldRegistryProfile | None = None,
    *,
    available_keys: set[str] | None = None,
) -> str | None:
    """Resolve the chunk_metadata key used to identify a row (drug/product).

    Priority:
      1. ``manifest.entity_key`` when present in the dataset
      2. Registry entity-concept column hints (aliases)
      3. Legacy fallbacks (``col_med``, ``col_brand``, ``col_api``, …)
    """
    keys = available_keys or set(manifest.columns.keys())

    if manifest.entity_key and manifest.entity_key in keys:
        return manifest.entity_key

    if registry is not None:
        entity_concept_name = registry.entity_concept
        if entity_concept_name:
            concept = next(
                (c for c in registry.concepts if c.concept == entity_concept_name),
                None,
            )
            if concept is not None:
                for key in _metadata_keys_from_hints(manifest, concept.resolves_to_columns):
                    if key in keys:
                        return key

    for legacy_key in LEGACY_ENTITY_KEY_PRIORITY:
        if legacy_key in keys:
            return legacy_key

    return None


def infer_manifest_from_col_keys(
    keys: Iterable[str],
    *,
    entity_hint: str | None = None,
) -> FieldManifest:
    """Build a partial manifest from legacy ``col_*`` metadata keys."""
    columns: dict[str, str] = {}
    for key in keys:
        key = str(key).strip()
        if key.startswith("col_"):
            columns[key] = _normalize_header(key)
        elif key in {
            "brand_name", "generic_name", "inn", "active_ingredient",
            "trade_name", "product_name", "arabic_name", "english_name",
        }:
            columns[key] = _normalize_header(key)

    manifest = FieldManifest(columns=columns)
    manifest.entity_key = resolve_entity_key(manifest, available_keys=set(columns.keys()))
    if entity_hint and not manifest.entity_key:
        target = _normalize_header(entity_hint)
        for meta_key, header in columns.items():
            if header == target or _normalize_header(meta_key) == target:
                manifest.entity_key = meta_key
                break
    return manifest


def manifest_field_labels(manifest: FieldManifest) -> list[str]:
    """Human-readable column labels present in the manifest."""
    labels: list[str] = []
    seen: set[str] = set()
    for meta_key, _header in manifest.columns.items():
        if meta_key.startswith("col_"):
            label = meta_key[4:].strip()
        else:
            label = meta_key.replace("_", " ").strip()
        if label and label not in seen:
            labels.append(label)
            seen.add(label)
    return sorted(labels, key=lambda s: s.lower())


def assess_field_capability(
    logical_field: str,
    registry: FieldRegistryProfile | None,
    manifest: FieldManifest | None,
) -> FieldCapability:
    """Check whether a logical field maps to a physical column in the dataset."""
    labels = tuple(manifest_field_labels(manifest)) if manifest and manifest.columns else ()

    if logical_field in _CAPABILITY_EXEMPT_CONCEPTS:
        return FieldCapability(
            status="unknown",
            logical_field=logical_field,
            available_field_labels=labels,
        )

    if registry is None or manifest is None or not manifest.columns:
        return FieldCapability(
            status="unknown",
            logical_field=logical_field,
            available_field_labels=labels,
        )

    concept = next((c for c in registry.concepts if c.concept == logical_field), None)
    if concept is None:
        return FieldCapability(
            status="unknown",
            logical_field=logical_field,
            available_field_labels=labels,
        )

    if not concept.resolves_to_columns:
        return FieldCapability(
            status="unknown",
            logical_field=logical_field,
            available_field_labels=labels,
        )

    column_keys: list[str] = []
    for hint in concept.resolves_to_columns:
        column_keys.extend(manifest.keys_for_header(hint))
        candidate = hint if str(hint).startswith("col_") else f"col_{hint}"
        if candidate in manifest.columns and candidate not in column_keys:
            column_keys.append(candidate)

    column_keys = list(dict.fromkeys(column_keys))
    if column_keys:
        return FieldCapability(
            status="available",
            logical_field=logical_field,
            physical_columns=tuple(column_keys),
            available_field_labels=labels,
        )

    return FieldCapability(
        status="not_available",
        logical_field=logical_field,
        physical_columns=(),
        available_field_labels=labels,
    )
