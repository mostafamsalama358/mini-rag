"""core/chunking/engine.py — chunking primitives (domain-agnostic).

Spec 002 Phase B/D: the splitter primitives live here so they are testable
without importing langchain/fastapi. ProcessController delegates to these.

Spec 006: ``row_chunk_*`` are thin compatibility shims over
``xlsx_parser`` + ``map_elements_to_chunks`` (no behavior change for callers).

Spec 007 Intelligent Chunking Engine:
  The Boundary Decision Pipeline (SemanticBoundaryEvaluator → BoundaryFeatures
  → BoundaryDecisionPolicy → BoundaryDecision → ChunkBuilder → ChunkValidator
  → ChunkSet) lives in ``core.chunking.strategies.semantic_structural`` and is
  selected via ``ChunkingProfile.strategy`` / ``get_chunking_strategy()``.
  See ``specs/007-intelligent-chunking-engine/plan.md``.

  ``row_chunk_dataframe`` / ``row_chunk_xlsx`` remain backward-compat shims that
  still call ``map_elements_to_chunks`` directly for legacy pharmacy row paths.
"""
from __future__ import annotations

from typing import Any


def _is_blank(value: Any) -> bool:
    try:
        import math
        if isinstance(value, float) and math.isnan(value):
            return True
    except Exception:
        pass
    return value is None or (isinstance(value, str) and not value.strip())


def row_chunk_dataframe(df, *, file_id: str, sheet_name: str) -> list[dict]:
    """Emit one {text, metadata} record per data row of a pandas DataFrame.

    Compatibility shim: builds table-row StructuralElements then maps them
    through the Document Intelligence chunk mapper.
    """
    if df is None or getattr(df, "empty", True):
        return []

    from core.document_intelligence.model import StructuralElement, make_element_id
    from core.document_intelligence.chunk_mapper import map_elements_to_chunks
    from fields.schemas import ElementChunkConfig

    columns = [str(col).strip() for col in df.columns]
    elements: list[StructuralElement] = []
    order = 0
    for offset, (_, row) in enumerate(df.iterrows(), start=2):
        fields = {
            col: "" if _is_blank(val) else str(val)
            for col, val in zip(columns, row.values)
        }
        if not any(value.strip() for value in fields.values()):
            continue
        elements.append(
            StructuralElement(
                id=make_element_id(file_id, f"sheet:0/row:{offset}"),
                type="table-row",
                order=order,
                fields=fields,
                provenance={
                    "sheet_name": sheet_name,
                    "row_index": offset,
                    "file_name": file_id,
                },
            )
        )
        order += 1

    config = {
        "table-row": ElementChunkConfig(
            group=False,
            metadata_keys=["sheet_name", "row_index"],
        )
    }
    records = map_elements_to_chunks(elements, config, file_name=file_id)
    # Preserve legacy text prefix used by pharmacy callers.
    for rec, el in zip(records, elements):
        line = ", ".join(f"{k}: {v}" for k, v in (el.fields or {}).items())
        rec["text"] = f"[{file_id} | {sheet_name}] {line}"
    return records


def row_chunk_xlsx(file_path: str, file_id: str) -> list[dict]:
    """Read an .xlsx and emit per-row chunk records across all sheets.

    Compatibility shim over XlsxDocumentParser + map_elements_to_chunks.
    """
    from core.document_intelligence.parsers.xlsx_parser import XlsxDocumentParser
    from core.document_intelligence.chunk_mapper import map_elements_to_chunks
    from core.field_resolution import build_field_manifest
    from fields.schemas import ElementChunkConfig

    class _RecordBatch(list):
        field_manifest = None

    model = XlsxDocumentParser().parse(file_path, file_id)
    config = {
        "table-row": ElementChunkConfig(
            group=False,
            metadata_keys=["sheet_name", "row_index"],
        )
    }
    records = _RecordBatch(
        map_elements_to_chunks(model.elements, config, file_name=file_id)
    )
    for rec, el in zip(records, model.elements):
        sheet = (el.provenance or {}).get("sheet_name", "")
        line = ", ".join(f"{k}: {v}" for k, v in (el.fields or {}).items())
        rec["text"] = f"[{file_id} | {sheet}] {line}"

    row_metadatas = [r["metadata"] for r in records]
    manifest = build_field_manifest(row_metadatas) if row_metadatas else None
    records.field_manifest = manifest
    return records
