from types import SimpleNamespace

from models.enums.ResponseEnums import ResponseSignal
from services.rag.pipeline.response_adapter import ResponseAdapter


def test_timeout_maps_to_rag_answer_timeout():
    adapter = ResponseAdapter()
    result = SimpleNamespace(
        outcome="timeout",
        answer_result=None,
        built_context=None,
        parse_result=None,
        retrieval_plan=None,
    )
    resp = adapter.from_unified_result(result, original_query="q")
    assert resp.signal == ResponseSignal.RAG_ANSWER_TIMEOUT
    assert resp.needs_clarification is False
    assert resp.answer


def test_clarification_never_empty_answer():
    adapter = ResponseAdapter()
    plan = SimpleNamespace(clarification_prompt="")
    result = SimpleNamespace(
        outcome="clarification",
        answer_result=None,
        built_context=None,
        parse_result=SimpleNamespace(query_plan=plan),
        retrieval_plan=None,
    )
    resp = adapter.from_unified_result(result, original_query="q")
    assert resp.signal == ResponseSignal.RAG_CLARIFICATION_NEEDED
    assert resp.needs_clarification is True
    assert resp.answer and "rephrase" in resp.answer.lower()


def test_no_context_signal():
    adapter = ResponseAdapter()
    result = SimpleNamespace(
        outcome="no_context",
        answer_result=None,
        built_context=None,
        parse_result=None,
        retrieval_plan=None,
    )
    resp = adapter.from_unified_result(result, original_query="q")
    assert resp.signal == ResponseSignal.RAG_NO_CONTEXT
