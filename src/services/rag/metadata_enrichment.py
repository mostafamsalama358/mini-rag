"""Generic chunk metadata enrichment driven by Domain Pack profiles.

Domain-specific patterns live in ``fields/{domain}/chunk_metadata.yaml``
(``MetadataEnrichmentProfile``). This module only applies declared rules.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from fields.schemas import (
    MetadataAliasDetector,
    MetadataEnrichmentProfile,
    MetadataEntityDetector,
    MetadataFieldPattern,
    MetadataProfile,
)


def _as_enrichment(
    enrichment: MetadataEnrichmentProfile | MetadataProfile | dict[str, Any] | None,
) -> MetadataEnrichmentProfile | None:
    if enrichment is None:
        return None
    if isinstance(enrichment, MetadataEnrichmentProfile):
        return enrichment if enrichment.enabled else None
    if isinstance(enrichment, MetadataProfile):
        profile = enrichment.enrichment
        return profile if profile.enabled else None
    if isinstance(enrichment, dict):
        if "enrichment" in enrichment:
            profile = MetadataEnrichmentProfile.model_validate(
                enrichment.get("enrichment") or {}
            )
        else:
            profile = MetadataEnrichmentProfile.model_validate(enrichment)
        return profile if profile.enabled else None
    return None


@lru_cache(maxsize=64)
def _compile(pattern: str) -> re.Pattern[str]:
    # Domain packs author human-facing phrases; match case-insensitively by default.
    return re.compile(pattern, re.IGNORECASE)


def extract_sections(
    text: str,
    *,
    section_header_pattern: str,
) -> list[str]:
    headers: list[str] = []
    for match in _compile(section_header_pattern).finditer(text or ""):
        if match.lastindex and match.lastindex >= 2:
            headers.append(f"{match.group(1)}. {match.group(2).strip()}")
        else:
            headers.append(match.group(0).strip())
    return headers


def extract_field_names(
    text: str,
    field_patterns: list[MetadataFieldPattern],
) -> list[str]:
    found: list[str] = []
    blob = text or ""
    for rule in field_patterns:
        if not rule.pattern or not rule.field:
            continue
        if _compile(rule.pattern).search(blob) and rule.field not in found:
            found.append(rule.field)
    return found


def _format_entity_from_match(template: str, match: re.Match[str]) -> str:
    entity = template
    for idx, group in enumerate(match.groups(), start=1):
        entity = entity.replace(f"{{{idx}}}", group or "")
    return entity.strip()


def _detector_context_hit(
    detector: MetadataEntityDetector,
    *,
    blob: str,
    file_name: str,
    head: str,
) -> re.Match[str] | bool | None:
    """Return match object / True when detector context matches, else None/False."""
    signals: list[bool] = []
    text_match: re.Match[str] | None = None

    if detector.file_name_regex:
        signals.append(bool(_compile(detector.file_name_regex).search(file_name)))
    if detector.text_head_regex:
        signals.append(bool(_compile(detector.text_head_regex).search(head)))
    if detector.text_head_prefix:
        signals.append(head.startswith(detector.text_head_prefix.lower()))
    if detector.text_regex:
        text_match = _compile(detector.text_regex).search(blob)
        signals.append(bool(text_match))

    if not signals:
        return None

    ok = any(signals) if detector.match_any else all(signals)
    if not ok:
        return None
    if detector.also_require and not _compile(detector.also_require).search(blob):
        return None
    return text_match if text_match is not None else True


def extract_entity_value(
    text: str,
    metadata: dict[str, Any] | None,
    entity_detectors: list[MetadataEntityDetector],
) -> str | None:
    meta = metadata or {}
    for key in ("entity", "brand_name", "product_name", "trade_name"):
        value = meta.get(key)
        if value not in (None, ""):
            return str(value).strip()

    fields_view = meta.get("fields")
    if isinstance(fields_view, dict):
        for key in ("med", "brand_name", "trade_name", "product_name", "Med"):
            value = fields_view.get(key)
            if value not in (None, ""):
                return str(value).strip()

    blob = text or ""
    file_name = str(meta.get("file_name") or "")
    head = blob[:240].lower()

    for detector in entity_detectors:
        hit = _detector_context_hit(
            detector, blob=blob, file_name=file_name, head=head
        )
        if not hit:
            continue
        if detector.entity_from_match and isinstance(hit, re.Match):
            return _format_entity_from_match(detector.entity_from_match, hit)
        if detector.entity:
            return detector.entity
    return None


def _aliases_from_inn_line(text: str) -> list[str]:
    """Parse structured leaflet line: ``INN / actives: paracetamol + ...``."""
    match = _compile(r"(?m)^INN\s*/\s*actives:\s*(.+)\s*$").search(text or "")
    if not match:
        return []
    raw = match.group(1)
    aliases: list[str] = []

    def _push(token: str) -> None:
        tok = re.sub(r"\b\d+(?:\.\d+)?\s*mg\b", "", token, flags=re.IGNORECASE)
        tok = re.sub(r"\s+", " ", tok).strip(" -/")
        if not tok or len(tok) < 3 or len(tok) > 40:
            return
        low = tok.lower()
        if any(x in low for x in ("typical", "as labelled", "as per", "local ", "variant")):
            return
        if tok not in aliases:
            aliases.append(tok)

    for paren in re.findall(r"\(([^)]+)\)", raw):
        for part in re.split(r"\s*(?:\+|,|;|\band\b)\s*", paren, flags=re.IGNORECASE):
            _push(part)
    lead = re.split(r"\(", raw, maxsplit=1)[0].strip()
    for part in re.split(r"\s*(?:\+|,|;|\band\b)\s*", lead, flags=re.IGNORECASE):
        _push(part)
    return aliases


def extract_entity_aliases(
    text: str,
    primary: str | None,
    alias_detectors: list[MetadataAliasDetector],
) -> list[str]:
    aliases: list[str] = []
    blob = text or ""
    primary_l = (primary or "").strip().lower()

    for detector in alias_detectors:
        ok = False
        if detector.text_regex and _compile(detector.text_regex).search(blob):
            ok = True
        if detector.primary_contains and primary_l and detector.primary_contains.lower() in primary_l:
            ok = True
        if not ok:
            continue
        for alias in detector.aliases:
            if alias and alias not in aliases:
                aliases.append(alias)

    for alias in _aliases_from_inn_line(blob):
        if alias not in aliases:
            aliases.append(alias)

    out: list[str] = []
    seen: set[str] = {primary_l} if primary_l else set()
    for alias in aliases:
        key = alias.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(alias)
    return out


def _primary_field_from_sections(
    sections: list[str],
    field_patterns: list[MetadataFieldPattern],
) -> str | None:
    for header in sections:
        for rule in field_patterns:
            if rule.pattern and _compile(rule.pattern).search(header):
                return rule.field
    return None


def enrich_chunk_metadata(
    metadata: dict[str, Any] | None,
    text: str,
    *,
    enrichment: MetadataEnrichmentProfile | MetadataProfile | dict[str, Any] | None = None,
    require_entity: bool = False,
) -> dict[str, Any]:
    """Return metadata copy enriched from the active Domain Pack profile."""
    meta = dict(metadata or {})
    rules = _as_enrichment(enrichment)
    if rules is None:
        # No pack enrichment — leave metadata unchanged (generic/legal default).
        if require_entity and not str(meta.get("entity") or "").strip():
            meta["metadata_reject_reason"] = "entity_missing"
        return meta

    field_names = extract_field_names(text, rules.field_patterns)
    sections = extract_sections(text, section_header_pattern=rules.section_header_pattern)

    # Pack enrichment owns field_name when enabled (overwrite stale process-time values).
    primary = _primary_field_from_sections(sections, rules.field_patterns)
    if primary is None and field_names:
        primary = field_names[0]
    if primary:
        meta["field_name"] = primary
        if primary not in field_names:
            field_names = [primary, *field_names]
    if field_names:
        # Prefer freshly extracted order from the pack; keep any extra legacy names after.
        merged: list[str] = list(field_names)
        existing = meta.get("field_names")
        if isinstance(existing, list):
            for name in existing:
                value = str(name)
                if value and value not in merged:
                    merged.append(value)
        meta["field_names"] = merged

    if sections and not meta.get("section"):
        meta["section"] = sections[0]
    if sections:
        meta["sections"] = sections

    entity_value = extract_entity_value(text, meta, rules.entity_detectors)
    if entity_value:
        # Overwrite stale entity labels when pack detectors fire.
        meta["entity"] = entity_value
        meta["entity_key"] = rules.entity_key_default or "entity"
        aliases = extract_entity_aliases(text, entity_value, rules.alias_detectors)
        if aliases:
            meta["entity_aliases"] = aliases

    if "metadata_schema_version" not in meta:
        meta["metadata_schema_version"] = "1"

    has_entity = bool(str(meta.get("entity") or "").strip())
    has_field = bool(str(meta.get("field_name") or "").strip())
    if has_entity and has_field:
        meta["metadata_completeness"] = "complete"
    elif has_entity or has_field:
        meta["metadata_completeness"] = "partial"
    else:
        meta["metadata_completeness"] = "legacy"

    if require_entity and not has_entity:
        meta["metadata_reject_reason"] = "entity_missing"

    return meta


def metadata_contract_ok(
    metadata: dict[str, Any] | None,
    *,
    strict: bool,
) -> tuple[bool, str | None]:
    """Validate retrieval-critical metadata. Strict mode requires entity + field_name."""
    meta = metadata or {}
    if not strict:
        return True, None
    if not str(meta.get("entity") or "").strip():
        return False, "entity_missing"
    if not str(meta.get("field_name") or "").strip() and not meta.get("field_names"):
        return False, "field_name_missing"
    return True, None
