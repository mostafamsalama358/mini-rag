"""Structured diagnostics for the indexing / metadata pipeline."""
from __future__ import annotations

import json
import logging
from typing import Any

from helpers.config import get_settings
from models.db_schemes import RetrievedDocument

logger = logging.getLogger("uvicorn.error")

_SEPARATOR = "-" * 40

_ENTITY_COL_KEYS = (
    "col_med",
    "col_brand_name",
    "col_trade_name",
    "col_product_name",
    "brand_name",
    "trade_name",
    "product_name",
    "entity",
    "entity_name",
)


def _emit(message: str) -> None:
    if get_settings().RAG_PIPELINE_DIAGNOSTICS:
        logger.info(message)
    else:
        logger.debug(message)


def _enabled() -> bool:
    return bool(get_settings().RAG_PIPELINE_DIAGNOSTICS)


def _trace_token() -> str:
    return (getattr(get_settings(), "RAG_INDEXING_TRACE_ENTITY", None) or "").strip().upper()


def _preview(text: str | None, limit: int = 200) -> str:
    raw = (text or "").replace("\n", " ").strip()
    if len(raw) <= limit:
        return raw
    return raw[:limit] + "..."


def _metadata_json(metadata: dict | None, *, limit: int = 4000) -> str:
    if not metadata:
        return "{}"
    try:
        rendered = json.dumps(metadata, ensure_ascii=False, sort_keys=True, default=str)
    except (TypeError, ValueError):
        rendered = repr(metadata)
    if len(rendered) > limit:
        return rendered[:limit] + "...(truncated)"
    return rendered


def extract_entity_from_metadata(
    metadata: dict | None,
    entity_key: str | None = None,
) -> str:
    """Best-effort entity label from chunk / vector metadata."""
    if not metadata:
        return ""

    if entity_key:
        value = metadata.get(entity_key)
        if value not in (None, ""):
            return str(value).strip()

    fields_view = metadata.get("fields")
    if isinstance(fields_view, dict):
        for header in ("med", "brand_name", "trade_name", "product_name", "Med"):
            value = fields_view.get(header)
            if value not in (None, ""):
                return str(value).strip()
        for value in fields_view.values():
            text = str(value or "").strip()
            if text and len(text) <= 80:
                return text

    for key in _ENTITY_COL_KEYS:
        value = metadata.get(key)
        if value not in (None, ""):
            return str(value).strip()

    return ""


def _should_log_chunk(metadata: dict | None, *, index: int, total: int) -> bool:
    if not _enabled():
        return False
    trace = _trace_token()
    if trace:
        haystack = _metadata_json(metadata).upper()
        text = (metadata or {}).get("chunk_text") or ""
        if trace in haystack or trace in str(text).upper():
            return True
    return index < 3 or index >= total - 1


def log_indexing_chunk(
    *,
    stage: str,
    document_id: int | str | None,
    chunk_id: int | str | None,
    chunk_order: int | None,
    metadata: dict | None,
    text: str | None,
    entity_key: str | None = None,
    field: str | None = None,
    index: int = 0,
    total: int = 1,
) -> None:
    if not _should_log_chunk(metadata, index=index, total=total):
        return

    entity = extract_entity_from_metadata(metadata, entity_key)
    lines = [
        _SEPARATOR,
        f"INDEXING CHUNK ({stage})",
        _SEPARATOR,
        f"document_id={document_id!r}",
        f"chunk_id={chunk_id!r}",
        f"chunk_order={chunk_order!r}",
        f"entity={entity!r}",
        f"entity_key={entity_key!r}",
        f"field={field!r}",
        f"has_fields_view={isinstance((metadata or {}).get('fields'), dict)}",
        f"metadata_keys={sorted((metadata or {}).keys())!r}",
        f"metadata={_metadata_json(metadata)}",
        f"preview={_preview(text)!r}",
        _SEPARATOR,
    ]
    _emit("\n".join(lines))


def log_indexing_batch_summary(
    *,
    stage: str,
    project_id: int | str,
    asset_name: str | None,
    chunk_count: int,
    entity_key: str | None = None,
    manifest_columns: int = 0,
) -> None:
    if not _enabled():
        return
    lines = [
        _SEPARATOR,
        f"INDEXING BATCH ({stage})",
        _SEPARATOR,
        f"project_id={project_id!r}",
        f"asset_name={asset_name!r}",
        f"chunk_count={chunk_count}",
        f"entity_key={entity_key!r}",
        f"manifest_columns={manifest_columns}",
        _SEPARATOR,
    ]
    _emit("\n".join(lines))


def log_field_manifest_persist(
    *,
    asset_name: str,
    entity_key: str | None,
    columns: dict[str, str],
    persisted: bool,
    error: str | None = None,
) -> None:
    if not _enabled():
        return
    lines = [
        _SEPARATOR,
        "FIELD MANIFEST",
        _SEPARATOR,
        f"asset_name={asset_name!r}",
        f"entity_key={entity_key!r}",
        f"column_count={len(columns)}",
        f"columns_sample={dict(list(columns.items())[:8])!r}",
        f"persisted={persisted}",
    ]
    if error:
        lines.append(f"error={error!r}")
    lines.append(_SEPARATOR)
    _emit("\n".join(lines))


def log_vector_insert_payload(
    *,
    collection_name: str,
    chunk_ids: list[int],
    metadata_batch: list[dict | None],
    texts: list[str],
) -> None:
    if not _enabled():
        return

    lines = [
        _SEPARATOR,
        "VECTOR INSERT PAYLOAD",
        _SEPARATOR,
        f"collection_name={collection_name!r}",
        f"batch_size={len(chunk_ids)}",
    ]
    trace = _trace_token()
    for idx, (chunk_id, meta, text) in enumerate(zip(chunk_ids, metadata_batch, texts)):
        if idx >= 3 and not trace:
            lines.append("...(remaining chunks omitted; set RAG_INDEXING_TRACE_ENTITY to trace)")
            break
        entity = extract_entity_from_metadata(meta)
        haystack = _metadata_json(meta).upper()
        if trace and trace not in haystack and trace not in (text or "").upper() and idx >= 3:
            continue
        lines.extend([
            "",
            f"[{idx + 1}] chunk_id={chunk_id!r}",
            f"entity={entity!r}",
            f"has_entity_key={bool(entity)}",
            f"has_fields_view={isinstance((meta or {}).get('fields'), dict)}",
            f"metadata={_metadata_json(meta)}",
            f"text_preview={_preview(text)!r}",
        ])
    lines.append(_SEPARATOR)
    _emit("\n".join(lines))


def log_raw_vector_metadata(
    documents: list[RetrievedDocument],
    *,
    stage: str,
    entity_key: str | None = None,
) -> None:
    if not _enabled() or not documents:
        return

    lines = [
        _SEPARATOR,
        f"RAW VECTOR METADATA ({stage})",
        _SEPARATOR,
        f"chunks={len(documents)}",
    ]
    trace = _trace_token()
    for idx, doc in enumerate(documents, start=1):
        meta = doc.metadata or {}
        entity = extract_entity_from_metadata(meta, entity_key)
        if trace and idx > 5:
            haystack = _metadata_json(meta).upper() + (doc.text or "").upper()
            if trace not in haystack:
                continue
        elif idx > 5 and not trace:
            lines.append("...(remaining chunks omitted)")
            break
        lines.extend([
            "",
            f"[{idx}]",
            f"chunk_id={meta.get('chunk_id')!r}",
            f"document_id={meta.get('asset_id')!r}",
            f"entity={entity!r}",
            f"entity_key={entity_key!r}",
            f"has_fields_view={isinstance(meta.get('fields'), dict)}",
            f"raw_metadata={_metadata_json(meta)}",
            f"text_preview={_preview(doc.text)!r}",
        ])
    lines.append(_SEPARATOR)
    _emit("\n".join(lines))


def log_grounding_rejection(
    documents: list[RetrievedDocument],
    *,
    entity_tokens: list[str],
    entity_key: str | None = None,
) -> None:
    if not _enabled() or not documents:
        return

    tokens_u = {(t or "").strip().upper() for t in entity_tokens if (t or "").strip()}
    lines = [
        _SEPARATOR,
        "GROUNDING REJECTION DETAIL",
        _SEPARATOR,
        f"entity_tokens={sorted(tokens_u)!r}",
        f"entity_key={entity_key!r}",
        f"input_chunks={len(documents)}",
    ]
    for idx, doc in enumerate(documents[:10], start=1):
        meta = doc.metadata or {}
        entity = extract_entity_from_metadata(meta, entity_key)
        text_hit = any(tok in (doc.text or "").upper() for tok in tokens_u)
        fields_hit = False
        fields_view = meta.get("fields")
        if isinstance(fields_view, dict):
            joined = " ".join(str(v) for v in fields_view.values()).upper()
            fields_hit = any(tok in joined for tok in tokens_u)
        col_hit = any(
            tok in str(meta.get(key) or "").upper()
            for key in _ENTITY_COL_KEYS
            for tok in tokens_u
        )
        lines.extend([
            "",
            f"[{idx}] chunk_id={meta.get('chunk_id')!r}",
            f"logged_entity={entity!r}",
            f"text_match={text_hit}",
            f"fields_match={fields_hit}",
            f"col_match={col_hit}",
            f"preview={_preview(doc.text)!r}",
        ])
    lines.append(_SEPARATOR)
    _emit("\n".join(lines))
