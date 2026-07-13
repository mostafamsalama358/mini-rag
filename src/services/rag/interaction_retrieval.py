"""Structured interaction retrieval for pharmacy (and similar) field packs.

Interaction rows are keyed by API/active-ingredient columns (e.g. col_API1 /
col_API2), while users ask by brand name (e.g. ACHTENON). This module
resolves brand → composition token, then loads interaction rows directly.
"""
from __future__ import annotations

import re

from fields.schemas import FieldRegistryProfile
from models.db_schemes import RetrievedDocument
from repositories.chunk_repository import ChunkModel
from core.field_resolution import FieldManifest, resolve_entity_key


def _dedupe_keys(keys: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for key in keys:
        if key and key not in seen:
            seen.add(key)
            ordered.append(key)
    return ordered


def entity_lookup_keys(
    field_manifest: FieldManifest,
    registry: FieldRegistryProfile,
) -> list[str]:
    keys: list[str] = []
    primary = resolve_entity_key(field_manifest, registry)
    if primary:
        keys.append(primary)
    entity_concept_name = registry.entity_concept
    if entity_concept_name:
        concept = next(
            (c for c in registry.concepts if c.concept == entity_concept_name),
            None,
        )
        if concept is not None:
            keys.extend(_metadata_keys_from_hints(field_manifest, concept.resolves_to_columns))
    return _dedupe_keys(keys) or ["col_med"]


def composition_metadata_keys(
    field_manifest: FieldManifest,
    registry: FieldRegistryProfile,
) -> list[str]:
    composition_name = registry.composition_concept
    if not composition_name:
        return []
    concept = next(
        (c for c in registry.concepts if c.concept == composition_name),
        None,
    )
    if concept is None:
        return []
    return _metadata_keys_from_hints(field_manifest, concept.resolves_to_columns)


def interaction_metadata_keys(
    field_manifest: FieldManifest,
    registry: FieldRegistryProfile,
) -> list[str]:
    headers: list[str] = []
    for pair in registry.interaction_column_pairs or []:
        headers.extend(str(header) for header in pair)
    keys = _metadata_keys_from_hints(field_manifest, headers)
    return keys or ["col_API1", "col_API2"]


def _metadata_keys_from_hints(
    field_manifest: FieldManifest,
    headers: list[str],
) -> list[str]:
    keys: list[str] = []
    for header in headers:
        keys.extend(field_manifest.keys_for_header(header))
        if not field_manifest.keys_for_header(header):
            h = (header or "").strip()
            if not h:
                continue
            keys.append(h if h.startswith("col_") else f"col_{h}")
    return _dedupe_keys(keys)


def normalize_api_token(raw: str) -> str | None:
    """Extract a single API token suitable for interaction table equality."""
    text = (raw or "").strip()
    if not text:
        return None
    first_part = text.split(",")[0].strip()
    token = re.split(r"\s+", first_part)[0].strip().upper()
    return token or None


async def resolve_composition_token(
    *,
    project_id: int,
    entity: str,
    chunk_model: ChunkModel,
    field_manifest: FieldManifest,
    registry: FieldRegistryProfile,
) -> str | None:
    """Map a brand/trade entity to its active-ingredient (API) token."""
    brand = (entity or "").strip().split()[0]
    if not brand:
        return None

    composition_keys = composition_metadata_keys(field_manifest, registry)
    if not composition_keys:
        return None

    for entity_key in entity_lookup_keys(field_manifest, registry):
        rows = await chunk_model.list_chunks_for_entity_prefix(
            project_id,
            entity_key=entity_key,
            entity_prefix=brand,
            limit=12,
        )
        for row in rows:
            metadata = row.get("metadata") or {}
            for comp_key in composition_keys:
                token = normalize_api_token(str(metadata.get(comp_key) or ""))
                if token:
                    return token
    return None


async def fetch_interaction_documents(
    *,
    project_id: int,
    entity: str,
    chunk_model: ChunkModel,
    field_manifest: FieldManifest,
    registry: FieldRegistryProfile,
    limit: int = 500,
) -> tuple[list[RetrievedDocument], str | None]:
    """Load interaction rows for *entity* via its resolved API/composition token."""
    api_token = await resolve_composition_token(
        project_id=project_id,
        entity=entity,
        chunk_model=chunk_model,
        field_manifest=field_manifest,
        registry=registry,
    )
    if not api_token:
        return [], None

    column_keys = interaction_metadata_keys(field_manifest, registry)
    rows = await chunk_model.list_drug_interactions_for_api(
        project_id,
        api_token,
        limit=limit,
        column_keys=column_keys,
    )
    documents = [
        RetrievedDocument(
            text=row.get("text") or "",
            score=1.0,
            metadata=row.get("metadata") or {},
        )
        for row in rows
    ]
    return documents, api_token
