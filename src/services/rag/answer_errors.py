"""User-facing /answer error copy that stays on the frozen signal set."""

from __future__ import annotations

from models.enums.ResponseEnums import ResponseSignal
from stores.llm.errors import VertexGenerationError

VERTEX_QUOTA_HTTP_STATUS = 503
VERTEX_QUOTA_MESSAGE = (
    "The answer service is temporarily unavailable due to generation quota limits. "
    "Please retry in a few minutes."
)


def domain_key_value(project) -> str:
    raw = getattr(project, "domain_key", None)
    return str(getattr(raw, "value", raw) or "").lower()


def scope_miss_message(domain_key: str | None) -> str:
    domain = str(getattr(domain_key, "value", domain_key) or "").lower()
    if domain == "pharmacy":
        return (
            "No indexed information was found for this medicine or topic in the "
            "current project. The drug may be missing from the corpus, or the "
            "question needs a clearer product name. Upload the relevant leaflet/"
            "interaction sheet and re-index, or ask about a medicine that is "
            "already indexed."
        )
    return (
        "No indexed information was found for this topic in the current project. "
        "The material may be missing from the corpus, or the question needs a "
        "clearer name. Upload the relevant file and re-index, or ask about a "
        "topic that is already indexed."
    )


def vertex_generation_error_body(exc: VertexGenerationError) -> tuple[int, dict[str, str]]:
    message = (
        VERTEX_QUOTA_MESSAGE
        if exc.category == "vertex_quota"
        else (
            "Could not generate an answer. Try rephrasing the question or retry shortly."
        )
    )
    return VERTEX_QUOTA_HTTP_STATUS, {
        "signal": ResponseSignal.RAG_ANSWER_ERROR.value,
        "message": message,
    }
