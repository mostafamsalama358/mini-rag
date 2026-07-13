"""ChunkValidator — quality gate producing structured ValidationReport."""

from __future__ import annotations

from core.chunking.models import Chunk, ChunkingStrategyConfig, ValidationReport

_RULE_MESSAGES: dict[str, str] = {
    "min_content": "Chunk text is empty or whitespace-only",
    "max_size": "Chunk text exceeds max_chars budget",
    "no_orphaned_heading": "Heading chunk has no child or following content",
    "no_cross_section_merge": "Chunk source elements span multiple sections",
    "no_mid_row_split": "Table-row element was split across chunks",
    "referential_integrity": "Chunk relationship references a missing chunk id",
    "figure_provenance": "Figure-placeholder chunk lacks figure provenance metadata",
}


class ChunkValidator:
    """Applies quality rules and returns a structured ValidationReport."""

    def __init__(self, config: ChunkingStrategyConfig | None = None) -> None:
        self.config = config or ChunkingStrategyConfig()

    def validate(self, chunks: list[Chunk]) -> ValidationReport:
        failed_rules: list[str] = []
        warnings: list[str] = []
        messages: list[str] = []
        chunk_ids = {
            c.identity.chunk_id
            for c in chunks
            if c.identity is not None and c.identity.chunk_id
        }

        for chunk in chunks:
            text = chunk.text or ""
            if not text.strip():
                self._record(failed_rules, messages, "min_content")

            if len(text) > self.config.max_chars:
                oversized_index = (chunk.metadata or {}).get("oversized_split_index")
                if oversized_index is None:
                    self._record(failed_rules, messages, "max_size")

            element_type = (chunk.structural_context.element_type if chunk.structural_context else None) or chunk.metadata.get("element_type")
            if element_type == "heading":
                has_children = bool(chunk.relationships.child_chunk_ids)
                if not has_children and len(text.strip()) == len(text):
                    self._record(failed_rules, messages, "no_orphaned_heading")

            if chunk.lineage and chunk.lineage.source_element_ids:
                section_ids = chunk.metadata.get("lineage_section_ids")
                if isinstance(section_ids, list) and len(set(section_ids)) > 1:
                    self._record(failed_rules, messages, "no_cross_section_merge")

            source_ids = chunk.metadata.get("source_element_ids") or []
            element_type_meta = chunk.metadata.get("element_type")
            if element_type_meta == "table-row" and len(source_ids) != 1:
                self._record(failed_rules, messages, "no_mid_row_split")

            rel = chunk.relationships
            for ref_id in (
                rel.parent_chunk_id,
                rel.previous_chunk_id,
                rel.next_chunk_id,
                *rel.child_chunk_ids,
            ):
                if ref_id and ref_id not in chunk_ids:
                    self._record(failed_rules, messages, "referential_integrity")
                    break

            if element_type_meta == "figure-placeholder":
                provenance = chunk.metadata.get("figure_id") or chunk.metadata.get("figure_ref")
                if not provenance:
                    self._record(warnings, messages, "figure_provenance")

        status = "pass"
        if failed_rules:
            status = "fail"
        elif warnings:
            status = "pass_with_warnings"

        return ValidationReport(
            status=status,  # type: ignore[arg-type]
            failed_rules=sorted(set(failed_rules)),
            warnings=sorted(set(warnings)),
            validation_messages=messages,
        )

    @staticmethod
    def _record(bucket: list[str], messages: list[str], rule_id: str) -> None:
        if rule_id not in bucket:
            bucket.append(rule_id)
        messages.append(_RULE_MESSAGES.get(rule_id, rule_id))
