"""Map StructuralElements → retrieval chunks (FR-005 / FR-006 / FR-007)."""

from __future__ import annotations

from typing import Any

from fields.schemas import ElementChunkConfig
from core.document_intelligence.model import StructuralElement

# Defaults when a type is missing from pack element_mapping (data-model.md §3).
_DEFAULT_GROUP: dict[str, bool] = {
    "paragraph": True,
    "list-item": True,
    "table-row": False,
    "section": False,
    "table": False,
    "list": False,
}


def _config_for(
    element_type: str,
    config: dict[str, ElementChunkConfig],
    default_max_chars: int,
) -> ElementChunkConfig:
    if element_type in config:
        cfg = config[element_type]
        if cfg.max_chunk_chars is None:
            return cfg.model_copy(update={"max_chunk_chars": default_max_chars})
        return cfg
    return ElementChunkConfig(
        group=_DEFAULT_GROUP.get(element_type, False),
        max_chunk_chars=default_max_chars,
        metadata_keys=[],
    )


def _render_element(element: StructuralElement) -> str:
    if element.type == "table-row" and element.fields is not None:
        return ", ".join(f"{k}: {v}" for k, v in element.fields.items())
    return element.text or ""


def _base_metadata(element: StructuralElement, text: str) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "element_type": element.type,
        "source_element_ids": [element.id],
        "char_count": len(text),
        **dict(element.provenance or {}),
    }
    if element.fields is not None:
        meta["fields"] = dict(element.fields)
        meta.update({f"col_{k}": v for k, v in element.fields.items()})
    return meta


def _split_oversized(text: str, max_chars: int, overlap: int) -> list[str]:
    """Documented FR-005 exception: split one oversized element's rendered text."""
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    start = 0
    step = max(1, max_chars - max(0, overlap))
    while start < len(text):
        end = min(len(text), start + max_chars)
        parts.append(text[start:end])
        if end >= len(text):
            break
        start += step
    return parts


def map_elements_to_chunks(
    elements: list[StructuralElement],
    config: dict[str, ElementChunkConfig],
    *,
    default_max_chars: int = 800,
    overlap: int = 0,
    file_name: str | None = None,
) -> list[dict[str, Any]]:
    """Convert ordered structural elements into chunk records.

    Returns list of ``{"text": str, "metadata": dict}``.
    """
    if not elements:
        return []

    chunks: list[dict[str, Any]] = []
    i = 0
    n = len(elements)

    while i < n:
        el = elements[i]
        cfg = _config_for(el.type, config, default_max_chars)
        max_chars = int(cfg.max_chunk_chars or default_max_chars)
        rendered = _render_element(el)

        # Oversized single element → internal split (FR-005 exception).
        if len(rendered) > max_chars and not cfg.group:
            for part_idx, part in enumerate(_split_oversized(rendered, max_chars, overlap)):
                meta = _base_metadata(el, part)
                meta["source_element_ids"] = [el.id]
                meta["oversized_split_index"] = part_idx
                if file_name:
                    meta["file_name"] = file_name
                for key in cfg.metadata_keys:
                    if key in el.provenance:
                        meta[key] = el.provenance[key]
                    elif el.fields and key in el.fields:
                        meta[key] = el.fields[key]
                chunks.append({"text": part, "metadata": meta})
            i += 1
            continue

        group: list[StructuralElement] = [el]
        group_text = rendered
        j = i + 1

        if cfg.group:
            while j < n:
                nxt = elements[j]
                if nxt.type != el.type:
                    break
                nxt_cfg = _config_for(nxt.type, config, default_max_chars)
                if not nxt_cfg.group:
                    break
                nxt_text = _render_element(nxt)
                candidate = f"{group_text}\n{nxt_text}" if group_text else nxt_text
                if len(candidate) > max_chars and group_text:
                    break
                # Single oversized next element: stop grouping; it will be handled alone.
                if len(nxt_text) > max_chars:
                    break
                group.append(nxt)
                group_text = candidate
                j += 1

        # If the lone element is still oversized under group=True, split it.
        if len(group) == 1 and len(group_text) > max_chars:
            for part_idx, part in enumerate(_split_oversized(group_text, max_chars, overlap)):
                meta = _base_metadata(el, part)
                meta["oversized_split_index"] = part_idx
                if file_name:
                    meta["file_name"] = file_name
                chunks.append({"text": part, "metadata": meta})
            i = j
            continue

        meta: dict[str, Any] = {
            "element_type": el.type,
            "source_element_ids": [g.id for g in group],
            "char_count": len(group_text),
        }
        if file_name:
            meta["file_name"] = file_name

        # Inherit provenance from first element; merge metadata_keys from all.
        meta.update(dict(group[0].provenance or {}))
        if len(group) == 1 and group[0].fields is not None:
            meta["fields"] = dict(group[0].fields)
            meta.update({f"col_{k}": v for k, v in group[0].fields.items()})

        for g in group:
            for key in cfg.metadata_keys:
                if key in (g.provenance or {}):
                    meta[key] = g.provenance[key]
                elif g.fields and key in g.fields:
                    meta[key] = g.fields[key]

        chunks.append({"text": group_text, "metadata": meta})
        i = j

    return chunks
