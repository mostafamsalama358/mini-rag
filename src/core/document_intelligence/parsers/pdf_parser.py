"""PDF → section/paragraph (+ best-effort table-row) StructuralElements."""

from __future__ import annotations

import re

from core.document_intelligence.errors import DocumentIntelligenceDegraded
from core.document_intelligence.model import DocumentModel, StructuralElement, make_element_id

_TABLE_LINE = re.compile(r"\S+\s{2,}\S+")


def _looks_like_table_block(lines: list[str]) -> bool:
    if len(lines) < 2:
        return False
    hits = sum(1 for line in lines if _TABLE_LINE.search(line) or "\t" in line)
    return hits >= max(2, len(lines) // 2)


def _split_table_row(line: str) -> dict[str, str]:
    if "\t" in line:
        cells = [c.strip() for c in line.split("\t") if c.strip()]
    else:
        cells = [c.strip() for c in re.split(r"\s{2,}", line) if c.strip()]
    return {f"col_{i + 1}": cell for i, cell in enumerate(cells)}


class PdfDocumentParser:
    def parse(self, file_path: str, file_id: str) -> DocumentModel:
        fingerprint = file_id
        try:
            from utils.pdf_ocr import load_pdf_with_ocr_fallback

            pages = load_pdf_with_ocr_fallback(file_path)
        except FileNotFoundError:
            raise
        except OSError:
            raise
        except Exception as exc:
            msg = str(exc).lower()
            if any(token in msg for token in ("cannot open", "not a pdf", "damaged", "corrupt")):
                raise
            raise DocumentIntelligenceDegraded("parse_error", str(exc)) from exc

        if not pages:
            raise DocumentIntelligenceDegraded("empty_content", "pdf produced no pages")

        elements: list[StructuralElement] = []
        order = 0
        for page_doc in pages:
            page_text = (getattr(page_doc, "page_content", None) or "").strip()
            meta = getattr(page_doc, "metadata", None) or {}
            page_num = meta.get("page")
            try:
                page_num = int(page_num) if page_num is not None else None
            except (TypeError, ValueError):
                page_num = None

            if not page_text:
                continue

            lines = [ln.rstrip() for ln in page_text.splitlines() if ln.strip()]
            if _looks_like_table_block(lines):
                table_id = make_element_id(
                    fingerprint,
                    f"page:{page_num or order}/table:0",
                )
                elements.append(
                    StructuralElement(
                        id=table_id,
                        type="table",
                        order=order,
                        text=page_text,
                        provenance={"page": page_num, "file_name": file_id},
                    )
                )
                order += 1
                for row_idx, line in enumerate(lines, start=1):
                    fields = _split_table_row(line)
                    if not fields:
                        continue
                    elements.append(
                        StructuralElement(
                            id=make_element_id(
                                fingerprint,
                                f"page:{page_num or 0}/table:0/row:{row_idx}",
                            ),
                            type="table-row",
                            order=order,
                            fields=fields,
                            provenance={
                                "page": page_num,
                                "row_index": row_idx,
                                "file_name": file_id,
                            },
                            parent_id=table_id,
                        )
                    )
                    order += 1
            else:
                elements.append(
                    StructuralElement(
                        id=make_element_id(fingerprint, f"page:{page_num or order}/section:0"),
                        type="section",
                        order=order,
                        text=page_text,
                        provenance={"page": page_num, "file_name": file_id},
                    )
                )
                order += 1

        if not elements:
            raise DocumentIntelligenceDegraded("empty_content", "pdf has no extractable text")

        return DocumentModel(
            asset_id=file_id,
            source_format="pdf",
            elements=elements,
            extraction_outcome="full",
        )
