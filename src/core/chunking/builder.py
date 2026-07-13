"""Stateful ChunkBuilder — assembles chunks with identity, relationships, and lineage."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from core.chunking.models import (
    BoundaryDecision,
    Chunk,
    ChunkIdentity,
    ChunkLineage,
    ChunkRelationships,
    ChunkingStrategyConfig,
    StructuralContext,
    compute_config_hash,
)
from core.document_intelligence.model import DocumentModel, StructuralElement

_SECTION_TYPES = frozenset({"section", "heading"})


def _render_element(element: StructuralElement) -> str:
    if element.type == "table-row" and element.fields is not None:
        return ", ".join(f"{k}: {v}" for k, v in element.fields.items())
    return element.text or ""


def _base_metadata(
    elements: list[StructuralElement],
    text: str,
    *,
    file_name: str | None,
) -> dict[str, Any]:
    primary = elements[0]
    meta: dict[str, Any] = {
        "element_type": primary.type,
        "source_element_ids": [el.id for el in elements],
        "char_count": len(text),
        **dict(primary.provenance or {}),
    }
    if file_name:
        meta["file_name"] = file_name
    if len(elements) == 1 and elements[0].fields is not None:
        meta["fields"] = dict(elements[0].fields)
        meta.update({f"col_{k}": v for k, v in elements[0].fields.items()})
    return meta


class _OversizedSplitter:
    """Splits one oversized element at paragraph → sentence → character boundaries."""

    @staticmethod
    def split(text: str, max_chars: int, overlap: int) -> list[str]:
        if len(text) <= max_chars:
            return [text]
        for sep in ("\n\n", "\n"):
            parts = _OversizedSplitter._split_by_separator(text, sep, max_chars, overlap)
            if len(parts) > 1:
                return parts
        sentence_parts = _OversizedSplitter._split_sentences(text, max_chars, overlap)
        if len(sentence_parts) > 1:
            return sentence_parts
        return _OversizedSplitter._split_chars(text, max_chars, overlap)

    @staticmethod
    def _split_by_separator(text: str, sep: str, max_chars: int, overlap: int) -> list[str]:
        raw_parts = text.split(sep)
        if len(raw_parts) <= 1:
            return [text]
        parts: list[str] = []
        current = ""
        for idx, piece in enumerate(raw_parts):
            candidate = piece if not current else f"{current}{sep}{piece}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    parts.append(current)
                current = piece
            if idx == len(raw_parts) - 1 and current:
                parts.append(current)
        return parts if parts else [text]

    @staticmethod
    def _split_sentences(text: str, max_chars: int, overlap: int) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        parts: list[str] = []
        current = ""
        for sentence in sentences:
            candidate = sentence if not current else f"{current} {sentence}"
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    parts.append(current)
                current = sentence
        if current:
            parts.append(current)
        return parts if parts else [text]

    @staticmethod
    def _split_chars(text: str, max_chars: int, overlap: int) -> list[str]:
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


class ChunkBuilder:
    """Stateful assembler for chunk lifecycle (research R9)."""

    def __init__(
        self,
        document_model: DocumentModel,
        config: ChunkingStrategyConfig,
        strategy_id: str,
        *,
        file_name: str | None = None,
    ) -> None:
        self.document_model = document_model
        self.config = config
        self.strategy_id = strategy_id
        self.file_name = file_name
        self._config_hash = compute_config_hash(config)
        self._asset_id = str(document_model.asset_id)
        self._chunks: list[Chunk] = []
        self._open_elements: list[StructuralElement] = []
        self._open_text = ""
        self._heading_stack: list[str] = []
        self._heading_titles: list[str] = []
        self._current_section_chunk_id: str | None = None
        self._last_close_decision: BoundaryDecision | None = None
        self._identity_assigned_after_close = False
        self._relationships_assigned_after_close = False

    @property
    def chunks(self) -> list[Chunk]:
        return list(self._chunks)

    def open_chunk(self, element: StructuralElement) -> None:
        self._open_elements = [element]
        self._open_text = _render_element(element)
        self._update_heading_stack(element)

    def append_element(self, element: StructuralElement, merge_decision: BoundaryDecision) -> None:
        rendered = _render_element(element)
        if self._open_text:
            self._open_text = f"{self._open_text}\n{rendered}"
        else:
            self._open_text = rendered
        self._open_elements.append(element)
        self._update_heading_stack(element)
        self._last_close_decision = merge_decision

    def close_chunk(self, split_decision: BoundaryDecision) -> None:
        if not self._open_elements:
            return
        self._last_close_decision = split_decision
        text = self._open_text
        max_chars = self.config.max_chars

        if len(self._open_elements) == 1 and len(text) > max_chars:
            for idx, part in enumerate(_OversizedSplitter.split(text, max_chars, self.config.overlap)):
                self._emit_chunk(
                    [self._open_elements[0]],
                    part,
                    BoundaryDecision(
                        decision="split",
                        applied_rule="oversized_element_fallback",
                        triggered_features=["size_budget"],
                        rationale="Single element exceeded max_chars; split at sub-boundary",
                    ),
                    oversized_split_index=idx,
                )
        else:
            self._emit_chunk(self._open_elements, text, split_decision)

        self._open_elements = []
        self._open_text = ""
        self._identity_assigned_after_close = True
        self._relationships_assigned_after_close = True

    def finalize(self) -> list[Chunk]:
        self._assign_prev_next_links()
        self._populate_child_chunk_ids()
        return self.chunks

    def _update_heading_stack(self, element: StructuralElement) -> None:
        if element.type == "heading":
            title = element.text or ""
            self._heading_stack = [element.id]
            self._heading_titles = [title]
        elif element.type == "section":
            title = element.text or ""
            self._heading_stack = [element.id]
            self._heading_titles = [title]

    def _emit_chunk(
        self,
        elements: list[StructuralElement],
        text: str,
        decision: BoundaryDecision,
        *,
        oversized_split_index: int | None = None,
    ) -> None:
        primary = elements[0]
        position = len(self._chunks)
        heading_path = list(self._heading_titles)

        lineage = ChunkLineage.model_construct(
            source_element_ids=[el.id for el in elements],
            applied_rule=decision.applied_rule,
            triggered_features=list(decision.triggered_features),
            rationale=decision.rationale,
            oversized_split_index=oversized_split_index,
        )

        sorted_ids = sorted(el.id for el in elements)
        identity_payload = (
            f"{self._asset_id}|{','.join(sorted_ids)}|{self.strategy_id}|{self._config_hash}"
        )
        chunk_id = f"ck_{hashlib.sha256(identity_payload.encode('utf-8')).hexdigest()[:16]}"

        identity = ChunkIdentity.model_construct(
            chunk_id=chunk_id,
            document_id=self._asset_id,
            strategy_id=self.strategy_id,
            source_element_ids=sorted_ids,
        )

        parent_chunk_id = self._current_section_chunk_id
        if primary.type in _SECTION_TYPES:
            parent_chunk_id = None

        relationships = ChunkRelationships.model_construct(parent_chunk_id=parent_chunk_id)

        if primary.type in _SECTION_TYPES:
            self._current_section_chunk_id = chunk_id

        structural_context = StructuralContext.model_construct(
            element_type=primary.type,
            heading_path=heading_path,
            position=position,
        )

        lineage_data = {
            "source_element_ids": lineage.source_element_ids,
            "applied_rule": lineage.applied_rule,
            "triggered_features": lineage.triggered_features,
            "rationale": lineage.rationale,
            "oversized_split_index": lineage.oversized_split_index,
        }

        metadata = _base_metadata(elements, text, file_name=self.file_name)
        metadata.update(
            {
                "chunk_id": chunk_id,
                "parent_chunk_id": parent_chunk_id,
                "previous_chunk_id": None,
                "next_chunk_id": None,
                "heading_path": heading_path,
                "chunk_position": position,
                "lineage": lineage_data,
                "child_chunk_ids": [],
            }
        )
        if oversized_split_index is not None:
            metadata["oversized_split_index"] = oversized_split_index

        chunk = Chunk.model_construct(
            text=text,
            metadata=metadata,
            identity=identity,
            relationships=relationships,
            lineage=lineage,
            structural_context=structural_context,
        )
        self._chunks.append(chunk)

    def _assign_prev_next_links(self) -> None:
        for idx, chunk in enumerate(self._chunks):
            prev_id = self._chunks[idx - 1].identity.chunk_id if idx > 0 and self._chunks[idx - 1].identity else None
            next_id = self._chunks[idx + 1].identity.chunk_id if idx + 1 < len(self._chunks) and self._chunks[idx + 1].identity else None
            chunk.relationships.previous_chunk_id = prev_id
            chunk.relationships.next_chunk_id = next_id
            chunk.metadata["previous_chunk_id"] = prev_id
            chunk.metadata["next_chunk_id"] = next_id

    def _populate_child_chunk_ids(self) -> None:
        children_by_parent: dict[str, list[str]] = {}
        for chunk in self._chunks:
            parent_id = chunk.relationships.parent_chunk_id
            if parent_id and chunk.identity:
                children_by_parent.setdefault(parent_id, []).append(chunk.identity.chunk_id)
        for chunk in self._chunks:
            if chunk.identity:
                chunk.relationships.child_chunk_ids = children_by_parent.get(chunk.identity.chunk_id, [])
                chunk.metadata["child_chunk_ids"] = list(chunk.relationships.child_chunk_ids)
