"""Page-level searchable detection for PDF hybrid routing."""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DEFAULT_MIN_TEXT_CHARS = 10


@dataclass(frozen=True)
class PageSearchability:
    """One PDF page's text-layer classification (1-indexed page numbers)."""

    page_num: int
    searchable: bool
    text_len: int


def _min_text_chars() -> int:
    try:
        from helpers.config import get_settings

        value = int(getattr(get_settings(), "PDF_SEARCHABLE_MIN_CHARS", DEFAULT_MIN_TEXT_CHARS))
        return max(1, value)
    except Exception:
        return DEFAULT_MIN_TEXT_CHARS


def classify_pdf_pages(pdf_path: str, *, min_text_chars: int | None = None) -> list[PageSearchability]:
    """Return per-page searchable flags using the PDF text layer (PyMuPDF)."""
    import fitz

    threshold = min_text_chars if min_text_chars is not None else _min_text_chars()
    doc = fitz.open(pdf_path)
    try:
        pages: list[PageSearchability] = []
        for idx in range(len(doc)):
            text = (doc[idx].get_text() or "").strip()
            text_len = len(text)
            pages.append(
                PageSearchability(
                    page_num=idx + 1,
                    searchable=text_len >= threshold,
                    text_len=text_len,
                )
            )
        searchable_count = sum(1 for p in pages if p.searchable)
        logger.info(
            "PDF page detect | file=%s pages=%s searchable=%s min_chars=%s",
            pdf_path,
            len(pages),
            searchable_count,
            threshold,
        )
        return pages
    finally:
        doc.close()


def searchable_ratio(pages: list[PageSearchability]) -> float:
    if not pages:
        return 0.0
    return sum(1 for p in pages if p.searchable) / float(len(pages))
