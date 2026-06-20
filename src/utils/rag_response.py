CLARIFICATION_MARKER = "CLARIFICATION_NEEDED"


def parse_rag_answer(raw: str | None) -> tuple[str | None, bool]:
    """Split an LLM reply into (text, needs_clarification)."""
    text = (raw or "").strip()
    if not text:
        return None, False

    normalized = text.upper()
    if not normalized.startswith(CLARIFICATION_MARKER):
        return text, False

    body = text[len(CLARIFICATION_MARKER):].lstrip(" \t:-\n").strip()
    return body or text, True
