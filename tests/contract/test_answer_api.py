"""Contract tests for frozen /answer JSON schema (spec 015)."""

from __future__ import annotations

from models.enums.ResponseEnums import ResponseSignal

_REQUIRED_200_KEYS = frozenset(
    {"signal", "answer", "needs_clarification", "full_prompt", "chat_history"}
)
_VALID_ANSWER_SIGNALS = frozenset(
    {
        ResponseSignal.RAG_ANSWER_SUCCESS.value,
        ResponseSignal.RAG_CLARIFICATION_NEEDED.value,
    }
)


def _assert_200_schema(payload: dict) -> None:
    assert _REQUIRED_200_KEYS.issubset(payload.keys())
    assert payload["signal"] in _VALID_ANSWER_SIGNALS
    assert isinstance(payload["needs_clarification"], bool)
    if payload["signal"] == ResponseSignal.RAG_CLARIFICATION_NEEDED.value:
        assert payload["needs_clarification"] is True
    if payload["signal"] == ResponseSignal.RAG_ANSWER_SUCCESS.value:
        assert payload["needs_clarification"] is False


def test_success_response_schema_keys():
    payload = {
        "signal": ResponseSignal.RAG_ANSWER_SUCCESS.value,
        "answer": "Take with food.",
        "needs_clarification": False,
        "full_prompt": "prompt",
        "chat_history": [],
    }
    _assert_200_schema(payload)


def test_clarification_response_schema_keys():
    payload = {
        "signal": ResponseSignal.RAG_CLARIFICATION_NEEDED.value,
        "answer": "Which drug?",
        "needs_clarification": True,
        "full_prompt": None,
        "chat_history": None,
    }
    _assert_200_schema(payload)


def test_no_context_error_schema():
    payload = {
        "signal": ResponseSignal.RAG_NO_CONTEXT.value,
        "message": "No indexed documents found for this project. Upload a file and wait for indexing to finish.",
    }
    assert payload["signal"] == "rag_no_context"
    assert "message" in payload


def test_answer_error_schema():
    payload = {
        "signal": ResponseSignal.RAG_ANSWER_ERROR.value,
        "message": "Could not generate an answer. Try rephrasing the question or re-indexing the project.",
    }
    assert payload["signal"] == "rag_answer_error"


def test_pipeline_answer_response_maps_to_api_keys():
    from services.rag.pipeline.response_adapter import ResponseAdapter

    adapter = ResponseAdapter()
    resp = adapter.from_legacy_tuple("ans", "prompt", [], False)
    api = {
        "signal": resp.signal.value,
        "answer": resp.answer,
        "needs_clarification": resp.needs_clarification,
        "full_prompt": resp.full_prompt,
        "chat_history": resp.chat_history,
    }
    _assert_200_schema(api)
