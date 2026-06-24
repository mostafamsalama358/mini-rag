# Read the PDF page by page
# → If the page contains actual text (selectable text), use it.
# → If the page is a scanned PDF or the text is very limited, run Gemini OCR on the page image.

import logging
import os
import re
import gc
import signal
import time
from contextlib import contextmanager
from dataclasses import dataclass

import fitz
import numpy as np
from PIL import Image

from utils.text_cleaning import clean_extracted_text

logger = logging.getLogger(__name__)

OCR_IMAGE_SCALE = 1.5
DEFAULT_OCR_ENGINE = "gemini"
MIN_TEXT_LENGTH = 10
MAX_LANG_SAMPLE_CHARS = 5000


@dataclass
class PdfPageDocument:
    page_content: str
    metadata: dict


def _normalize_ocr_lang(lang_code: str | None) -> str:
    if not lang_code:
        return "en"
    if lang_code.lower().replace("_", "-").split("-")[0] == "ar":
        return "ar"
    return "en"


def _default_ocr_language() -> str:
    try:
        from helpers.config import get_settings

        return _normalize_ocr_lang(get_settings().PRIMARY_LANG)
    except Exception:
        return "en"


def _get_ocr_settings():
    try:
        from helpers.config import get_settings

        return get_settings()
    except Exception:
        return None


def _configured_ocr_scale() -> float:
    settings = _get_ocr_settings()
    try:
        return float(getattr(settings, "OCR_IMAGE_SCALE", OCR_IMAGE_SCALE))
    except (TypeError, ValueError):
        return OCR_IMAGE_SCALE


def _configured_page_timeout() -> int:
    settings = _get_ocr_settings()
    try:
        return max(10, int(getattr(settings, "OCR_PAGE_TIMEOUT_SECONDS", 120)))
    except (TypeError, ValueError):
        return 120


def _configured_ocr_engine() -> str:
    settings = _get_ocr_settings()
    engine = (getattr(settings, "OCR_ENGINE", None) or DEFAULT_OCR_ENGINE).lower().strip()
    if engine not in {"gemini", "docling"}:
        logger.warning("Unknown OCR_ENGINE=%r; falling back to gemini", engine)
        return DEFAULT_OCR_ENGINE
    return engine


class OcrPageTimeout(TimeoutError):
    pass


@contextmanager
def _ocr_timeout(seconds: int):
    if not hasattr(signal, "SIGALRM"):
        yield
        return

    def _handle_timeout(signum, frame):
        raise OcrPageTimeout(f"OCR page timed out after {seconds} seconds")

    old_handler = signal.signal(signal.SIGALRM, _handle_timeout)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def _collect_pdf_text_samples(doc: fitz.Document) -> str:
    parts: list[str] = []
    collected = 0

    for page_num in range(len(doc)):
        text = doc[page_num].get_text().strip()
        if not text:
            continue

        parts.append(text)
        collected += len(text)
        if collected >= MAX_LANG_SAMPLE_CHARS:
            break

    return "\n".join(parts)[:MAX_LANG_SAMPLE_CHARS]


def _detect_language_from_text(text: str) -> str | None:
    cleaned = text.strip()
    if len(cleaned) < MIN_TEXT_LENGTH:
        return None

    arabic_chars = len(re.findall(r"[\u0600-\u06ff\u0750-\u077f]", cleaned))
    latin_chars = len(re.findall(r"[A-Za-z]", cleaned))

    if arabic_chars >= 3 and arabic_chars >= latin_chars:
        return "ar"
    if arabic_chars >= 1 and latin_chars == 0:
        return "ar"
    if latin_chars >= 3 and latin_chars > arabic_chars:
        return "en"
    if arabic_chars > latin_chars:
        return "ar"
    return None


def _resolve_ocr_language(doc: fitz.Document) -> str:
    sample_text = _collect_pdf_text_samples(doc)
    detected = _detect_language_from_text(sample_text)
    if detected:
        return detected

    for page_num in range(min(3, len(doc))):
        page_text = doc[page_num].get_text().strip()
        page_detected = _detect_language_from_text(page_text)
        if page_detected:
            return page_detected

    if doc.language:
        return _normalize_ocr_lang(doc.language)

    return _default_ocr_language()


def _page_to_image(page: fitz.Page, scale: float | None = None) -> np.ndarray:
    scale = scale or _configured_ocr_scale()
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n
    )
    if pix.n == 4:
        img = img[:, :, :3]
    return img


def _extract_text_with_gemini(page: fitz.Page) -> str:
    from utils.gemini_ocr import extract_text_from_page_image

    pil_image = Image.fromarray(_page_to_image(page))
    return extract_text_from_page_image(pil_image)


def _extract_text_with_docling(page: fitz.Page, lang: str) -> str:
    from utils.docling_ocr import extract_text_from_page_image

    pil_image = Image.fromarray(_page_to_image(page))
    return extract_text_from_page_image(pil_image, lang=lang)


def _extract_text_with_ocr(
    page: fitz.Page, lang: str, page_num: int, pdf_path: str, engine: str
) -> str:
    timeout_seconds = _configured_page_timeout()
    started = time.monotonic()

    logger.info(
        "Starting OCR | engine=%s lang=%s page=%s timeout=%ss file=%s",
        engine,
        lang,
        page_num,
        timeout_seconds,
        pdf_path,
    )

    try:
        with _ocr_timeout(timeout_seconds):
            if engine == "docling":
                text = _extract_text_with_docling(page, lang)
            else:
                text = _extract_text_with_gemini(page)
    except OcrPageTimeout:
        logger.exception("OCR timed out | page=%s file=%s", page_num, pdf_path)
        return ""
    except Exception:
        logger.exception("OCR failed | engine=%s page=%s file=%s", engine, page_num, pdf_path)
        return ""

    logger.info(
        "Finished OCR | engine=%s page=%s chars=%s elapsed=%.2fs file=%s",
        engine,
        page_num,
        len(text or ""),
        time.monotonic() - started,
        pdf_path,
    )
    return text


def load_pdf_with_ocr_fallback(pdf_path: str) -> list[PdfPageDocument]:
    doc = fitz.open(pdf_path)
    pages: list[PdfPageDocument] = []

    try:
        ocr_lang = _resolve_ocr_language(doc)
        ocr_engine = _configured_ocr_engine()
        logger.info(
            "Resolved OCR language '%s' and engine '%s' for %s",
            ocr_lang,
            ocr_engine,
            pdf_path,
        )

        file_name = os.path.basename(pdf_path)
        extracted_texts: list[str] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text().strip()
            ocr_used = False

            if len(text) < MIN_TEXT_LENGTH:
                logger.info(
                    "Page %s in %s has little extractable text; running OCR",
                    page_num + 1,
                    pdf_path,
                )
                text = _extract_text_with_ocr(
                    page, ocr_lang, page_num + 1, pdf_path, ocr_engine
                )
                ocr_used = True

            text = clean_extracted_text(text)
            if not text:
                continue

            extracted_texts.append(text)

            pages.append(
                PdfPageDocument(
                    page_content=text,
                    metadata={
                        "file_name": file_name,
                        "page": page_num + 1,
                        "source_type": "pdf",
                        "ocr_engine": ocr_engine,
                        "ocr_used": ocr_used,
                        "ocr_lang": ocr_lang if ocr_used else None,
                    },
                )
            )
            if ocr_used:
                gc.collect()

        resolved_lang = _detect_language_from_text(" ".join(extracted_texts)) or ocr_lang
        for page_doc in pages:
            if page_doc.metadata.get("ocr_used"):
                page_doc.metadata["ocr_lang"] = resolved_lang
    finally:
        doc.close()

    return pages
