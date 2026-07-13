"""Pre-parse normalization only — Unicode, Arabic diacritics, digits, whitespace."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

_AR_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u0640]")
_EASTERN_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize_arabic_letters(text: str) -> str:
    """Letter-level Arabic normalization (no Latin OCR mangling)."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = _AR_DIACRITICS.sub("", normalized)
    normalized = re.sub(r"[أإآٱ]", "ا", normalized)
    normalized = re.sub(r"ة", "ه", normalized)
    normalized = re.sub(r"ى", "ي", normalized)
    normalized = re.sub(r"ؤ", "و", normalized)
    normalized = re.sub(r"ئ", "ي", normalized)
    return normalized


def normalize_query_text(text: str, config: Any | None = None) -> str:
    """Normalize a user query before semantic parse / retrieval."""
    if not text:
        return ""

    data = config
    if hasattr(config, "model_dump"):
        data = config.model_dump()
    if not isinstance(data, dict):
        data = {}

    ar_cfg = data.get("arabic_normalization")
    en_cfg = data.get("english_normalization")
    num_cfg = data.get("number_normalization")
    do_ar = True if ar_cfg is None else bool(
        ar_cfg is True or (isinstance(ar_cfg, dict) and ar_cfg.get("enabled", True))
    )
    do_en = True if en_cfg is None else bool(
        en_cfg is True or (isinstance(en_cfg, dict) and en_cfg.get("enabled", True))
    )
    do_num = True if num_cfg is None else bool(
        num_cfg is True or (isinstance(num_cfg, dict) and num_cfg.get("enabled", True))
    )

    out = unicodedata.normalize("NFKC", text)
    if do_ar:
        out = normalize_arabic_letters(out)
    if do_num:
        out = out.translate(_EASTERN_DIGITS)
    if do_en:
        out = re.sub(r"[A-Za-z]+", lambda m: m.group(0).lower(), out)
    out = re.sub(r"\s+", " ", out).strip()
    return out
