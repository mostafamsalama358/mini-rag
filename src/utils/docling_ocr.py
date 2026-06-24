"""Docling OCR wrapper using RapidOCR with the PaddlePaddle backend.

Docling does not ship a dedicated PaddleOCR plugin; RapidOCR can run the same
models via ``backend="paddle"`` (requires ``rapidocr-paddle``).
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

_converter = None
_converter_lang: str | None = None
_converter_scale: float | None = None


def _normalize_ocr_lang(lang_code: str | None) -> str:
    if not lang_code:
        return "en"
    primary = lang_code.lower().replace("_", "-").split("-")[0]
    if primary == "ar":
        return "ar"
    return "en"


def _rapidocr_langs(lang: str) -> list[str]:
    if lang == "ar":
        return ["ar", "en"]
    return ["en"]


def _configured_image_scale() -> float:
    try:
        from helpers.config import get_settings

        return float(getattr(get_settings(), "OCR_IMAGE_SCALE", 1.5))
    except Exception:
        return 1.5


def _get_converter(lang: str, image_scale: float):
    global _converter, _converter_lang, _converter_scale

    if _converter is not None and _converter_lang == lang and _converter_scale == image_scale:
        return _converter

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
    from docling.document_converter import DocumentConverter, ImageFormatOption

    pipeline_options = PdfPipelineOptions(
        do_ocr=True,
        ocr_options=RapidOcrOptions(
            lang=_rapidocr_langs(lang),
            backend="paddle",
        ),
        images_scale=image_scale,
    )

    _converter = DocumentConverter(
        format_options={
            InputFormat.IMAGE: ImageFormatOption(pipeline_options=pipeline_options),
        }
    )
    _converter_lang = lang
    _converter_scale = image_scale
    logger.info(
        "Initialized Docling OCR converter | backend=paddle lang=%s scale=%.2f",
        lang,
        image_scale,
    )
    return _converter


def extract_text_from_page_image(pil_image: Image.Image, lang: str | None = None) -> str:
    """Run Docling OCR on a single page image and return plain text."""
    normalized_lang = _normalize_ocr_lang(lang)
    image_scale = _configured_image_scale()
    converter = _get_converter(normalized_lang, image_scale)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        pil_image.save(tmp_path, format="PNG")

    try:
        result = converter.convert(str(tmp_path))
        document = result.document
        text = (document.export_to_markdown() or "").strip()
        if not text:
            logger.warning("Docling OCR returned empty text for page image")
        return text
    except Exception:
        logger.exception("Docling OCR failed for page image")
        return ""
    finally:
        tmp_path.unlink(missing_ok=True)
