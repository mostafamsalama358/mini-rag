"""XLSX → table-row StructuralElements (FR-004, research R8)."""

from __future__ import annotations

from typing import Any

from core.document_intelligence.errors import DocumentIntelligenceDegraded
from core.document_intelligence.model import DocumentModel, StructuralElement, make_element_id

# Bound element materialization for large sheets (research R8).
_ROW_BATCH_SIZE = 500


def _is_blank(value: Any) -> bool:
    try:
        import math

        if isinstance(value, float) and math.isnan(value):
            return True
    except Exception:
        pass
    return value is None or (isinstance(value, str) and not value.strip())


def _rows_from_dataframe(
    df,
    *,
    file_id: str,
    sheet_name: str,
    sheet_index: int,
    order_start: int,
    fingerprint: str,
) -> tuple[list[StructuralElement], int]:
    if df is None or getattr(df, "empty", True):
        return [], order_start

    columns = [str(col).strip() for col in df.columns]
    elements: list[StructuralElement] = []
    order = order_start

    for offset, (_, row) in enumerate(df.iterrows(), start=2):
        fields = {
            col: "" if _is_blank(val) else str(val)
            for col, val in zip(columns, row.values)
        }
        if not any(value.strip() for value in fields.values()):
            continue
        path = f"sheet:{sheet_index}/row:{offset}"
        elements.append(
            StructuralElement(
                id=make_element_id(fingerprint, path),
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
        # Batch boundary: yield control points for very large sheets.
        if len(elements) % _ROW_BATCH_SIZE == 0:
            pass

    return elements, order


class XlsxDocumentParser:
    """Parse .xlsx into one table-row element per data row across all sheets."""

    def parse(self, file_path: str, file_id: str) -> DocumentModel:
        import pandas as pd

        fingerprint = file_id
        try:
            dfs = pd.read_excel(file_path, sheet_name=None)
        except FileNotFoundError:
            raise
        except OSError:
            raise
        except Exception as exc:
            # Corrupted zip / unreadable workbook → hard failure (FR-011).
            # pandas/openpyxl raise various errors; treat open failures as hard.
            msg = str(exc).lower()
            if any(
                token in msg
                for token in ("no such file", "not a zip", "bad zipfile", "permission")
            ):
                raise
            raise DocumentIntelligenceDegraded(
                "parse_error",
                str(exc),
            ) from exc

        if not dfs:
            raise DocumentIntelligenceDegraded("empty_content", "workbook has no sheets")

        elements: list[StructuralElement] = []
        order = 0
        for sheet_index, (sheet_name, df) in enumerate(dfs.items()):
            sheet_elements, order = _rows_from_dataframe(
                df,
                file_id=file_id,
                sheet_name=str(sheet_name),
                sheet_index=sheet_index,
                order_start=order,
                fingerprint=fingerprint,
            )
            elements.extend(sheet_elements)

        if not elements:
            raise DocumentIntelligenceDegraded("empty_content", "no data rows found")

        return DocumentModel(
            asset_id=file_id,
            source_format="xlsx",
            elements=elements,
            extraction_outcome="full",
        )
