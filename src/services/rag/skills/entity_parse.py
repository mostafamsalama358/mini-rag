"""Entity-only parse for Skill-bound requests (021).

Does NOT classify intent, field, operation, capability, or recommend_mode.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from core.query_parser.grounding import _LATIN_TOKEN_RE, infer_entity_from_query
from core.query_parser.json_extract import extract_json_object
from core.query_parser.normalize import normalize_query_text
from core.query_parser.parser import (
    _LATIN_ENTITY_STOPWORDS,
    _PRODUCT_LINE_SECONDS,
    _recover_latin_brand_entity,
)
from services.FieldRegistry import FieldProfile

logger = logging.getLogger("uvicorn.error")

_ENTITY_ONLY_SYSTEM = (
    "You extract entities and slots from user questions for a retrieval system. "
    "Do NOT infer intent, field, operation, skill, or recommendation mode. "
    "Return ONLY JSON with keys: entities (array of strings), primary_entity "
    "(string|null), need_text (string|null), slots (object with optional age, "
    "weight, gender, dose, disease)."
)

# English pair connectors + Arabic "و" / "مع" between drug mentions
# (including tight ")و(" forms used in Arabic UI copy).
_PAIR_SPLIT_RE = re.compile(
    r"(?:"
    r"\b(?:with|and|vs\.?|versus|/|&)\b"
    r"|"
    r"(?<=[\w\)])\s*و\s*(?=[\w\(])"
    r"|"
    r"\s+مع\s+"
    r")",
    flags=re.IGNORECASE,
)

_PAREN_RE = re.compile(r"[()（）\[\]]+")


@dataclass
class EntityParseResult:
    entities: list[str] = field(default_factory=list)
    primary_entity: str | None = None
    need_text: str | None = None
    slots: dict[str, Any] = field(default_factory=dict)
    canonical_query: str = ""
    latency_ms: float = 0.0
    used_llm: bool = False
    error: str | None = None


def _strip_entity_wrappers(text: str) -> str:
    return _PAREN_RE.sub(" ", text or "").strip()


def _append_unique(found: list[str], candidate: str | None) -> None:
    text = _strip_entity_wrappers(str(candidate or "")).strip(" ,.;:")
    if not text:
        return
    if text.upper() in {e.upper() for e in found}:
        return
    found.append(text)


def _recover_all_latin_brands(query: str) -> list[str]:
    """Collect every distinct Latin brand-like token (not only the best one)."""
    cleaned = _strip_entity_wrappers(query)
    found: list[str] = []

    # Pair-split sides (English and/with + Arabic و/مع).
    parts = [p for p in _PAIR_SPLIT_RE.split(cleaned) if p and p.strip()]
    if len(parts) <= 1:
        parts = [cleaned]
    for part in parts:
        _append_unique(found, _recover_latin_brand_entity(part.strip()))

    # Scan all Latin tokens so "Congestal … Warfarin" keeps both even when
    # pair-split fails (e.g. unusual spacing).
    tokens = _LATIN_TOKEN_RE.findall(cleaned or "")
    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        upper = tok.upper()
        if upper in _LATIN_ENTITY_STOPWORDS or len(tok) < 4:
            idx += 1
            continue
        parts_tok = [tok]
        j = idx + 1
        while j < len(tokens) and tokens[j].upper() in _PRODUCT_LINE_SECONDS:
            parts_tok.append(tokens[j])
            j += 1
        # Prefer capitalized brands; still keep long lowercase INNs (warfarin).
        if tok[0].isupper() or len(tok) >= 6:
            _append_unique(found, " ".join(parts_tok))
        idx = j if j > idx + 1 else idx + 1

    return found


def _heuristic_entities(
    query: str,
    *,
    catalog_terms: list[str] | None,
    fingerprint_index: dict[str, list[str]] | None,
    min_score: float,
    entity_aliases: dict[str, str] | None,
) -> list[str]:
    found: list[str] = []
    cleaned = _strip_entity_wrappers(query or "")

    entity, _ = infer_entity_from_query(
        cleaned,
        catalog_terms,
        fingerprint_index,
        min_score=min_score,
        entity_aliases=entity_aliases,
    )
    _append_unique(found, entity)

    for brand in _recover_all_latin_brands(cleaned):
        _append_unique(found, brand)

    # Per-side catalog grounding for pair questions (second drug may be INN-only).
    for part in _PAIR_SPLIT_RE.split(cleaned):
        part = part.strip()
        if not part:
            continue
        side_entity, _ = infer_entity_from_query(
            part,
            catalog_terms,
            fingerprint_index,
            min_score=min_score,
            entity_aliases=entity_aliases,
        )
        _append_unique(found, side_entity)
        _append_unique(found, _recover_latin_brand_entity(part))

    return found


def _merge_entity_lists(*lists: list[str]) -> list[str]:
    merged: list[str] = []
    for items in lists:
        for item in items or []:
            _append_unique(merged, item)
    return merged


async def entity_parse_async(
    query: str,
    *,
    profile: FieldProfile,
    generation_client: Any | None = None,
    catalog_terms: list[str] | None = None,
    catalog_fingerprint_index: dict[str, list[str]] | None = None,
) -> EntityParseResult:
    """Skill-bound entity extraction only."""
    started = time.perf_counter()
    normalized = normalize_query_text(query, profile.config)
    parser_profile = profile.parser_profile
    min_score = float(parser_profile.entity_grounding.min_score or 0.82)
    aliases = dict(parser_profile.entity_grounding.entity_aliases or {})

    heuristic = _heuristic_entities(
        normalized,
        catalog_terms=catalog_terms,
        fingerprint_index=catalog_fingerprint_index,
        min_score=min_score,
        entity_aliases=aliases,
    )

    result = EntityParseResult(
        entities=list(heuristic),
        primary_entity=heuristic[0] if heuristic else None,
        canonical_query=normalized,
        used_llm=False,
    )

    # Prefer LLM when available to catch multi-entity / slots; still entity-only schema.
    if generation_client is not None and hasattr(generation_client, "generate_text"):
        try:
            prompt = (
                f"{_ENTITY_ONLY_SYSTEM}\n\nUser question:\n{normalized}\n\nJSON:"
            )
            raw = await generation_client.generate_text(prompt=prompt)
            payload_text = extract_json_object(str(raw or ""))
            if payload_text:
                payload = json.loads(payload_text)
                if isinstance(payload, dict):
                    ents = payload.get("entities") or []
                    llm_entities: list[str] = []
                    if isinstance(ents, list):
                        llm_entities = [
                            str(e).strip() for e in ents if e and str(e).strip()
                        ]
                    # Keep heuristic drugs when LLM under-extracts (common on
                    # Arabic "X و Y" pair questions).
                    result.entities = _merge_entity_lists(llm_entities, heuristic)
                    primary = payload.get("primary_entity")
                    if primary:
                        result.primary_entity = str(primary).strip()
                    elif result.entities:
                        result.primary_entity = result.entities[0]
                    need = payload.get("need_text")
                    if need:
                        result.need_text = str(need).strip()
                    slots = payload.get("slots")
                    if isinstance(slots, dict):
                        result.slots = {
                            k: v for k, v in slots.items() if v not in (None, "", [])
                        }
                    result.used_llm = True
        except Exception as exc:
            logger.debug("entity_parse_llm_failed err=%s", exc)
            result.error = type(exc).__name__

    if not result.primary_entity and result.entities:
        result.primary_entity = result.entities[0]
    if not result.canonical_query:
        result.canonical_query = normalized
    # Enrich canonical with entities for retrieval text
    if result.entities:
        result.canonical_query = " ".join(result.entities) + " " + normalized

    result.latency_ms = (time.perf_counter() - started) * 1000.0
    return result
