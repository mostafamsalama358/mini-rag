import re

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


def detect_query_language(text: str, default: str = "en") -> str:
    """Return 'ar' when the query contains Arabic script, else default."""
    if not text or not _ARABIC_RE.search(text):
        return default
    return "ar"
