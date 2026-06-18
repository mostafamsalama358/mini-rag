# Read the PDF page by page
# → If the page contains actual text (selectable text), use it.

# → If the page is a scanned PDF or the text is very limited, enable OCR and read the text from the image.

import logging
import os
import re
from dataclasses import dataclass

# Avoid oneDNN-related CPU inference errors on some platforms.
os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")

import fitz
import numpy as np

from utils.text_cleaning import clean_extracted_text

logger = logging.getLogger(__name__)

OCR_IMAGE_SCALE = 2.5

MIN_TEXT_LENGTH = 10
MAX_LANG_SAMPLE_CHARS = 5000
OCR_LANGS = ("ar", "en")

_ocr_engines: dict[str, object] = {}


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


def _get_ocr_engine(lang: str):
    from paddleocr import PaddleOCR

    paddle_lang = _normalize_ocr_lang(lang)
    engine = _ocr_engines.get(paddle_lang)
    if engine is None:
        engine = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang=paddle_lang,
        )
        _ocr_engines[paddle_lang] = engine
    return engine


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


def _is_arabic_text(text: str) -> bool:
    arabic_chars = len(re.findall(r"[\u0600-\u06ff\u0750-\u077f]", text))
    latin_chars = len(re.findall(r"[A-Za-z]", text))
    return arabic_chars >= 3 and arabic_chars >= latin_chars


def _detect_language_from_text(text: str) -> str | None:
    cleaned = text.strip()
    if len(cleaned) < MIN_TEXT_LENGTH:
        return None
    return "ar" if _is_arabic_text(cleaned) else "en"


def _ocr_result_quality(texts: list[str], scores: list[float]) -> float:
    if not texts or not scores:
        return 0.0

    combined = " ".join(texts).strip()
    letter_count = sum(
        1
        for char in combined
        if char.isalpha() or "\u0600" <= char <= "\u06ff"
    )
    if letter_count < 2:
        return 0.0

    return (sum(scores) / len(scores)) * min(1.0, letter_count / 5)


def _probe_ocr_language(page: fitz.Page) -> str | None:
    img = _page_to_image(page)
    best_lang = None
    best_score = 0.0

    for lang in OCR_LANGS:
        result = _get_ocr_engine(lang).predict(img)
        if not result:
            continue

        res = result[0].json.get("res", {})
        texts = res.get("rec_texts", [])
        scores = res.get("rec_scores", [])
        score = _ocr_result_quality(texts, scores)
        combined = " ".join(texts)

        if lang == "ar" and _is_arabic_text(combined):
            score += 0.2
        elif lang == "en" and not _is_arabic_text(combined):
            score += 0.2

        if score > best_score:
            best_score = score
            best_lang = lang

    return best_lang


def _resolve_ocr_language(doc: fitz.Document) -> str:
    sample_text = _collect_pdf_text_samples(doc)
    detected = _detect_language_from_text(sample_text)
    if detected:
        return detected

    if doc.language:
        return _normalize_ocr_lang(doc.language)

    if len(doc) > 0:
        probed = _probe_ocr_language(doc[0])
        if probed:
            return probed

    return _default_ocr_language()


def _sort_ocr_texts_by_boxes(texts: list[str], boxes: list) -> list[str]:
    if not texts:
        return []

    if not boxes or len(boxes) != len(texts):
        return texts

    indexed_texts = []
    for text, box in zip(texts, boxes):
        if not box:
            indexed_texts.append((0.0, 0.0, text))
            continue

        y_coords = [point[1] for point in box]
        x_coords = [point[0] for point in box]
        indexed_texts.append((min(y_coords), min(x_coords), text))

    indexed_texts.sort(key=lambda item: (item[0], item[1]))
    return [text for _, _, text in indexed_texts]


def _page_to_image(page: fitz.Page, scale: float = OCR_IMAGE_SCALE) -> np.ndarray:
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n
    )
    if pix.n == 4:
        img = img[:, :, :3]
    return img


def _extract_text_with_ocr(page: fitz.Page, lang: str) -> str:
    result = _get_ocr_engine(lang).predict(_page_to_image(page))

    if not result:
        return ""

    res = result[0].json.get("res", {})
    rec_texts = res.get("rec_texts", [])
    rec_boxes = res.get("rec_boxes", [])
    ordered_texts = _sort_ocr_texts_by_boxes(rec_texts, rec_boxes)
    return " ".join(ordered_texts)


def load_pdf_with_ocr_fallback(pdf_path: str) -> list[PdfPageDocument]:
    doc = fitz.open(pdf_path)
    pages: list[PdfPageDocument] = []

    try:
        ocr_lang = _resolve_ocr_language(doc)
        logger.info("Resolved OCR language '%s' for %s", ocr_lang, pdf_path)

        file_name = os.path.basename(pdf_path)

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
                text = _extract_text_with_ocr(page, ocr_lang)
                ocr_used = True

            text = clean_extracted_text(text)

            pages.append(
                PdfPageDocument(
                    page_content=text,
                    metadata={
                        "file_name": file_name,
                        "page": page_num + 1,
                        "source_type": "pdf",
                        "ocr_used": ocr_used,
                        "ocr_lang": ocr_lang if ocr_used else None,
                    },
                )
            )
    finally:
        doc.close()

    return pages
