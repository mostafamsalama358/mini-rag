"""Answer-route quota and domain-aware miss copy."""

from models.enums.ResponseEnums import ResponseSignal
from services.rag.answer_errors import scope_miss_message, vertex_generation_error_body
from stores.llm.errors import VertexGenerationError


def test_scope_miss_pharmacy_mentions_medicine():
    text = scope_miss_message("pharmacy")
    assert "medicine" in text
    assert "drug" in text


def test_scope_miss_madrsty_does_not_mention_medicine():
    text = scope_miss_message("madrsty")
    assert "medicine" not in text
    assert "drug" not in text
    assert "topic" in text


def test_vertex_quota_returns_503_with_frozen_error_signal():
    status_code, body = vertex_generation_error_body(
        VertexGenerationError("vertex_quota", "Vertex AI generation quota exhausted")
    )
    assert status_code == 503
    assert body["signal"] == ResponseSignal.RAG_ANSWER_ERROR.value
    assert "quota" in body["message"].lower()
