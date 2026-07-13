"""CSV → table-row StructuralElements (FR-004)."""

from __future__ import annotations

from typing import Any

from core.document_intelligence.errors import DocumentIntelligenceDegraded
from core.document_intelligence.model import DocumentModel, StructuralElement, make_element_id


def _is_blank(value: Any) -> bool:
    try:
        import math

        if isinstance(value, float) and math.isnan(value):
            return True
    except Exception:
        pass
    return value is None or (isinstance(value, str) and not value.strip())


class CsvDocumentParser:
    def parse(self, file_path: str, file_id: str) -> DocumentModel:
        import pandas as pd

        fingerprint = file_id
        try:
            df = pd.read_csv(file_path)
        except FileNotFoundError:
            raise
        except OSError:
            raise
        except Exception as exc:
            raise DocumentIntelligenceDegraded("parse_error", str(exc)) from exc

        if df is None or getattr(df, "empty", True):
            raise DocumentIntelligenceDegraded("empty_content", "csv has no data rows")

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
            path = f"sheet:0/row:{offset}"
            elements.append(
                StructuralElement(
                    id=make_element_id(fingerprint, path),
                    type="table-row",
                    order=order,
                    fields=fields,
                    provenance={
                        "sheet_name": "csv",
                        "row_index": offset,
                        "file_name": file_id,
                    },
                )
            )
            order += 1

        if not elements:
            raise DocumentIntelligenceDegraded("empty_content", "csv has no usable rows")

        return DocumentModel(
            asset_id=file_id,
            source_format="csv",
            elements=elements,
            extraction_outcome="full",
        )
