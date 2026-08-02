"""PDF → StructuralElements via hybrid OpenDataLoader + OCR routing.

Flow:
  Upload PDF
    → detect searchable pages (text layer)
    → searchable ratio above threshold → OpenDataLoader (+ OCR for non-searchable pages)
    → otherwise → legacy PyMuPDF/OCR path
    → DocumentModel → chunking/embedding (unchanged sole ingest path)
"""

from __future__ import annotations

import logging
import re

from core.document_intelligence.errors import DocumentIntelligenceDegraded
from core.document_intelligence.model import DocumentModel, StructuralElement, make_element_id

logger = logging.getLogger(__name__)

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


def _parser_mode() -> str:
    try:
        from helpers.config import get_settings

        mode = (getattr(get_settings(), "PDF_PARSER_MODE", None) or "hybrid").lower().strip()
    except Exception:
        mode = "hybrid"
    if mode not in {"hybrid", "legacy"}:
        logger.warning("Unknown PDF_PARSER_MODE=%r; using hybrid", mode)
        return "hybrid"
    return mode


def _searchable_ratio_threshold() -> float:
    try:
        from helpers.config import get_settings

        value = float(getattr(get_settings(), "PDF_SEARCHABLE_RATIO_THRESHOLD", 0.05))
    except Exception:
        value = 0.05
    return min(1.0, max(0.0, value))


def _pages_to_elements(
    pages: list,
    *,
    file_id: str,
    start_order: int = 0,
) -> list[StructuralElement]:
    elements: list[StructuralElement] = []
    order = start_order
    fingerprint = file_id

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
        parser_tag = meta.get("parser") or ("ocr" if meta.get("ocr_used") else "pymupdf")
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
                    provenance={
                        "page": page_num,
                        "file_name": file_id,
                        "parser": parser_tag,
                    },
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
                            "parser": parser_tag,
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
                    provenance={
                        "page": page_num,
                        "file_name": file_id,
                        "parser": parser_tag,
                    },
                )
            )
            order += 1

    return elements


class PdfDocumentParser:
    def parse(self, file_path: str, file_id: str) -> DocumentModel:
        mode = _parser_mode()
        if mode == "legacy":
            return self._parse_legacy(file_path, file_id)

        try:
            return self._parse_hybrid(file_path, file_id)
        except DocumentIntelligenceDegraded:
            raise
        except FileNotFoundError:
            raise
        except OSError:
            raise
        except Exception as exc:
            msg = str(exc).lower()
            if any(token in msg for token in ("cannot open", "not a pdf", "damaged", "corrupt")):
                raise
            logger.warning(
                "Hybrid PDF parse failed; falling back to legacy | file=%s err=%s",
                file_path,
                exc,
            )
            return self._parse_legacy(file_path, file_id)

    def _parse_hybrid(self, file_path: str, file_id: str) -> DocumentModel:
        from utils.opendataloader_pdf import (
            convert_pdf_to_json,
            covered_page_numbers,
            is_opendataloader_available,
            json_to_structural_elements,
        )
        from utils.pdf_page_detect import classify_pdf_pages, searchable_ratio

        try:
            page_flags = classify_pdf_pages(file_path)
        except FileNotFoundError:
            raise
        except OSError:
            raise
        except Exception as exc:
            msg = str(exc).lower()
            if any(token in msg for token in ("cannot open", "not a pdf", "damaged", "corrupt")):
                raise
            raise DocumentIntelligenceDegraded("parse_error", str(exc)) from exc

        if not page_flags:
            raise DocumentIntelligenceDegraded("empty_content", "pdf produced no pages")

        ratio = searchable_ratio(page_flags)
        threshold = _searchable_ratio_threshold()
        odl_ready = is_opendataloader_available()

        logger.info(
            "PDF hybrid routing | file=%s pages=%s searchable_ratio=%.3f threshold=%.3f odl=%s",
            file_path,
            len(page_flags),
            ratio,
            threshold,
            odl_ready,
        )

        if ratio < threshold or not odl_ready:
            if not odl_ready and ratio >= threshold:
                logger.warning(
                    "OpenDataLoader unavailable (package/Java); using legacy OCR path | file=%s",
                    file_path,
                )
            return self._parse_legacy(file_path, file_id)

        odl_doc = convert_pdf_to_json(file_path)
        elements = json_to_structural_elements(odl_doc, file_id=file_id)
        covered = covered_page_numbers(elements)

        # Non-searchable pages always need OCR. Also OCR searchable pages ODL missed.
        need_ocr = {
            p.page_num
            for p in page_flags
            if (not p.searchable) or (p.page_num not in covered)
        }

        if need_ocr:
            from utils.pdf_ocr import extract_pages_with_ocr

            ocr_pages = extract_pages_with_ocr(file_path, need_ocr)
            # Avoid duplicating pages already covered by ODL.
            ocr_pages = [
                page
                for page in ocr_pages
                if int((getattr(page, "metadata", None) or {}).get("page") or 0) not in covered
            ]
            start_order = (max((el.order for el in elements), default=-1) + 1) if elements else 0
            elements.extend(
                _pages_to_elements(ocr_pages, file_id=file_id, start_order=start_order)
            )

        if not elements:
            raise DocumentIntelligenceDegraded(
                "empty_content",
                "hybrid pdf parse produced no extractable elements",
            )

        # Stable reading order: page then original order.
        elements.sort(
            key=lambda el: (
                (el.provenance or {}).get("page") is None,
                (el.provenance or {}).get("page") or 0,
                el.order,
            )
        )
        for idx, el in enumerate(elements):
            el.order = idx

        return DocumentModel(
            asset_id=file_id,
            source_format="pdf",
            elements=elements,
            extraction_outcome="full",
        )

    def _parse_legacy(self, file_path: str, file_id: str) -> DocumentModel:
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

        elements = _pages_to_elements(pages, file_id=file_id)
        if not elements:
            raise DocumentIntelligenceDegraded("empty_content", "pdf has no extractable text")

        return DocumentModel(
            asset_id=file_id,
            source_format="pdf",
            elements=elements,
            extraction_outcome="full",
        )
