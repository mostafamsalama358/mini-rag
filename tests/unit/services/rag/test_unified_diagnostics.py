import logging
from types import SimpleNamespace

from services.rag.diagnostics import (
    log_unified_outcome,
    log_unified_parse,
    log_unified_plan,
    log_unified_retrieval,
)


def test_log_unified_stages_emit_info(caplog, monkeypatch):
    monkeypatch.setattr(
        "services.rag.diagnostics.get_settings",
        lambda: SimpleNamespace(RAG_PIPELINE_DIAGNOSTICS=True),
    )
    plan = type(
        "P",
        (),
        {
            "needs_clarification": False,
            "entity": "ibuprofen",
            "field": "dosage",
            "operation": "lookup",
            "clarification_prompt": None,
        },
    )()
    parse = type("R", (), {"query_plan": plan, "error": None})()
    retrieval_plan = type(
        "RP",
        (),
        {
            "plan_id": "p1",
            "intent": "lookup",
            "channels": ["dense"],
            "top_k": 5,
        },
    )()
    cand = type(
        "C",
        (),
        {
            "score": 0.9,
            "text": "Do not take more than 6 tablets",
            "metadata": {"field_name": "dosage", "entity": "MediQuick Ibuprofen"},
            "chunk_id": "c1",
        },
    )()

    with caplog.at_level(logging.INFO):
        log_unified_parse(parse_result=parse, domain="pharmacy")
        log_unified_plan(plan=retrieval_plan)
        log_unified_retrieval(
            scope={"entity_prefix": "ibuprofen", "field_key": "dosage"},
            candidates=[cand],
        )
        log_unified_outcome(outcome="answer", answer_result=None)

    text = "\n".join(r.message for r in caplog.records)
    assert "UNIFIED PARSE" in text
    assert "UNIFIED PLAN" in text
    assert "UNIFIED RETRIEVAL" in text
    assert "UNIFIED OUTCOME" in text
