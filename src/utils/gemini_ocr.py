import io
import logging

import vertexai
from PIL import Image
from vertexai.generative_models import GenerativeModel, Part

logger = logging.getLogger(__name__)

_GEMINI_OCR_MODEL: GenerativeModel | None = None
_GEMINI_OCR_MODEL_ID: str | None = None

_OCR_PROMPT = """Extract all text from this document page exactly as written.
Preserve Arabic and English text, numbers, headings, tables, and reading order.
Return only the extracted text with no commentary or markdown."""


def _get_gemini_ocr_model() -> GenerativeModel:
    global _GEMINI_OCR_MODEL, _GEMINI_OCR_MODEL_ID

    from helpers.config import get_settings

    settings = get_settings()
    model_id = getattr(settings, "OCR_GEMINI_MODEL_ID", None) or settings.GENERATION_MODEL_ID

    if _GEMINI_OCR_MODEL is None or _GEMINI_OCR_MODEL_ID != model_id:
        vertexai.init(
            project=settings.VERTEX_PROJECT_ID,
            location=settings.VERTEX_LOCATION,
        )
        _GEMINI_OCR_MODEL = GenerativeModel(model_id)
        _GEMINI_OCR_MODEL_ID = model_id

    return _GEMINI_OCR_MODEL


def extract_text_from_page_image(pil_image: Image.Image) -> str:
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()

    model = _get_gemini_ocr_model()
    response = model.generate_content(
        [
            Part.from_text(_OCR_PROMPT),
            Part.from_data(data=image_bytes, mime_type="image/png"),
        ],
        generation_config={
            "max_output_tokens": 4096,
            "temperature": 0,
        },
    )

    text = (response.text or "").strip()
    if not text:
        logger.warning("Gemini OCR returned empty text for page image")

    return text
