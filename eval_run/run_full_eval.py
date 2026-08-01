"""End-to-end Answer Quality evaluation harness.

Runs the REAL production pipeline code (retrieval_planner -> retrieval_engine ->
evidence_orchestrator -> context_builder -> answer_generation -> answer_quality)
against a hand-labeled synthetic corpus (see corpus.py) because:
  1. No live Postgres/pgvector instance is available in this environment.
  2. No LLM API keys are configured (.env absent) -> no live embedding or
     generation calls are possible.
  3. The in-repo golden dataset (tests/fixtures/answer_quality) has only 3
     fixtures and no IR relevance judgments, so Recall/Precision/MRR/NDCG
     cannot be computed against it.

This script substitutes TF-IDF/Jaccard retrievers (see retrievers.py) for the
dense/keyword backends and a MockLLM for the generation backend, but every
other stage runs the ACTUAL src/core/* pipeline classes. All numbers printed
are REAL outputs of REAL code on a REAL (if synthetic) corpus, not invented.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from corpus import CORPUS_BY_ID, QUERIES, EvalQuery  # noqa: E402
from ir_metrics import mrr, ndcg_at_k, precision_at_k, recall_at_k  # noqa: E402
from retrievers import JaccardKeywordRetriever, TfidfSemanticRetriever  # noqa: E402

from core.query_parser.schema import ParseResult, QueryPlan  # noqa: E402
from core.retrieval_planner.models import RetrievalPlannerConfig  # noqa: E402
from core.retrieval_planner.registry import RetrievalPlannerRegistry  # noqa: E402

from core.retrieval_engine.budget.enforcer import BudgetEnforcer  # noqa: E402
from core.retrieval_engine.expansion.entity_hint import EntityHintExpander  # noqa: E402
from core.retrieval_engine.fusion.rrf import RRFScoreFuser  # noqa: E402
from core.retrieval_engine.models import RetrievalEngineConfig  # noqa: E402
from core.retrieval_engine.pipeline import RetrievalEnginePipeline  # noqa: E402
from core.retrieval_engine.reranking.passthrough import PassthroughReranker  # noqa: E402
from core.retrieval_engine.router import StrategyRouter  # noqa: E402
from core.retrieval_engine.tracing.tracer import RetrievalTracer  # noqa: E402

from core.evidence_orchestrator.config import EvidenceOrchestratorConfig  # noqa: E402
from core.evidence_orchestrator.registry import EvidenceOrchestratorRegistry  # noqa: E402

from core.context_builder.config import BudgetReservations, ContextBuilderConfig  # noqa: E402
from core.context_builder.registry import ContextBuilderRegistry  # noqa: E402

from core.answer_generation.config import resolve_answer_generation_config  # noqa: E402
from core.answer_generation.registry import AnswerGenerationRegistry  # noqa: E402

from core.answer_quality.config import AnswerQualityConfig  # noqa: E402
from core.answer_quality.models import GoldenTestFixture, PipelineSnapshot  # noqa: E402
from core.answer_quality.registry import AnswerQualityRegistry  # noqa: E402

from stores.llm.LLMInterface import LLMInterface  # noqa: E402


class _MockLLMEnums:
    SYSTEM = type("EnumValue", (), {"value": "system"})()


class MockLLM(LLMInterface):
    """Deterministic stand-in for a live generation backend (no API key
    configured in this environment). See module docstring for the resulting
    evaluation limitation: no real-model hallucination/accuracy is measured.
    """

    enums = _MockLLMEnums()

    def __init__(self, response: str | None = None) -> None:
        self.response = response or json.dumps({"answer": "", "confidence_note": None})
        self.call_count = 0

    def set_generation_model(self, model_id: str) -> None:
        _ = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int) -> None:
        _ = model_id, embedding_size

    def generate_text(self, prompt, chat_history=None, max_output_tokens=None, temperature=None, *, response_mime_type=None, response_schema=None):
        _ = prompt, chat_history, max_output_tokens, temperature, response_mime_type, response_schema
        return self.response

    async def generate_text_async(self, prompt, chat_history=None, max_output_tokens=None, temperature=None, *, response_mime_type=None, response_schema=None):
        self.call_count += 1
        _ = prompt, chat_history, max_output_tokens, temperature, response_mime_type, response_schema
        return self.response

    def embed_text(self, text: str, document_type: str | None = None):
        _ = text, document_type
        return []

    def construct_prompt(self, prompt: str, role: str):
        return {"role": role, "content": prompt}


# --------------------------------------------------------------------------
# Planner wiring (real RetrievalPlannerPipeline, hand-built ParseResult since
# query_parser needs a live LLM which is unavailable here).
# --------------------------------------------------------------------------

_planner_registry = RetrievalPlannerRegistry()
_planner_registry.register_defaults()
_planner_config = RetrievalPlannerConfig(diagnostics_enabled=True)
_planner_pipeline = _planner_registry.build_pipeline(_planner_config)


def _build_parse_result(q: EvalQuery) -> ParseResult:
    entities = [q.entity] if q.entity else []
    qp = QueryPlan(
        entity=q.entity,
        entities=entities,
        field=q.field,
        operation=q.operation,
        scope="all",
        language="en",
        filters={},
        confidence=0.9 if q.category != "ambiguous" else None,
        needs_clarification=False,
    )
    return ParseResult(
        original_query=q.text,
        canonical_query=q.text,
        query_plan=qp,
        used_llm=False,
        latency_ms=0.0,
    )


# --------------------------------------------------------------------------
# Retrieval engine wiring (real pipeline + real RRF fusion, TF-IDF/Jaccard
# retrievers substituting for embedding/full-text backends).
# --------------------------------------------------------------------------

_engine_config = RetrievalEngineConfig(hybrid_components=["semantic", "keyword"])
_retrievers = {
    "semantic": TfidfSemanticRetriever(),
    "keyword": JaccardKeywordRetriever(),
}
_engine_pipeline = RetrievalEnginePipeline(
    expander=EntityHintExpander(),
    router=StrategyRouter(lambda s: _retrievers.get(s)),
    fuser=RRFScoreFuser(),
    reranker=PassthroughReranker(),
    budget_enforcer=BudgetEnforcer(),
    tracer_factory=RetrievalTracer,
    config=_engine_config,
)

_eo_config = EvidenceOrchestratorConfig()
_eo_orchestrator = EvidenceOrchestratorRegistry().build_orchestrator(_eo_config)

_cb_config = ContextBuilderConfig(
    total_context_window=4000,
    reservations=BudgetReservations(system_prompt=300, question=100, output=600),
)
_cb_pipeline = ContextBuilderRegistry.build(_cb_config)

_ag_config = resolve_answer_generation_config("generic")


def _mock_llm_for(q: EvalQuery, context) -> MockLLM:
    """Deterministically fill citation placeholders with real item_ids in the
    order blocks were included, then wrap as a MockLLM response. If the LLM
    cannot ground the answer (no blocks) the pipeline itself emits no_answer.
    """
    if not q.good_answer or not context.ordered_blocks:
        return MockLLM(response=json.dumps({"answer": "", "confidence_note": None}))
    item_ids = [b.item_id for b in context.ordered_blocks]
    answer = q.good_answer
    for i, item_id in enumerate(item_ids):
        answer = answer.replace(f"[[CITE{i}]]", f"[{item_id}]")
    # Strip any unresolved placeholders (more citations templated than blocks present).
    import re

    answer = re.sub(r"\[\[CITE\d+\]\]", "", answer)
    return MockLLM(response=json.dumps({"answer": answer, "confidence_note": None}))


async def run_query(q: EvalQuery) -> dict:
    record: dict = {"query_id": q.query_id, "category": q.category, "text": q.text}

    # ---- Planner ----
    parse_result = _build_parse_result(q)
    t0 = time.perf_counter()
    plan = _planner_pipeline.plan(parse_result, _planner_config)
    planner_latency_ms = (time.perf_counter() - t0) * 1000.0
    record["planner"] = {
        "intent_category": plan.intent.category,
        "intent_confidence": plan.intent.confidence,
        "expected_intent": q.expected_intent,
        "intent_correct": plan.intent.category == q.expected_intent,
        "clarification_required": plan.clarification_required,
        "strategies": list(plan.retrieval_strategies),
        "max_evidence_units": plan.retrieval_limits.max_evidence_units,
        "max_candidates": plan.retrieval_limits.max_candidates,
        "scope": plan.retrieval_limits.scope,
        "latency_ms": planner_latency_ms,
        "plan_id": plan.metadata.plan_id,
    }

    if plan.clarification_required:
        record["retrieval"] = None
        record["evidence"] = None
        record["context"] = None
        record["answer"] = {"no_answer": True, "reason": "clarification_required"}
        record["quality"] = None
        return record

    # ---- Retrieval engine ----
    t0 = time.perf_counter()
    result = await _engine_pipeline.execute(plan)
    engine_latency_ms = (time.perf_counter() - t0) * 1000.0
    ranked_ids = [c.chunk_id for c in result.candidates]
    relevant = set(q.relevant_chunk_ids)

    record["retrieval"] = {
        "ranked_chunk_ids": ranked_ids,
        "relevant_chunk_ids": sorted(relevant),
        "candidate_count": len(result.candidates),
        "partial": result.partial,
        "latency_ms": engine_latency_ms,
        "recall_at_5": recall_at_k(ranked_ids, relevant, 5),
        "recall_at_10": recall_at_k(ranked_ids, relevant, 10),
        "recall_at_20": recall_at_k(ranked_ids, relevant, 20),
        "precision_at_5": precision_at_k(ranked_ids, relevant, 5),
        "precision_at_10": precision_at_k(ranked_ids, relevant, 10),
        "mrr": mrr(ranked_ids, relevant),
        "ndcg_at_10": ndcg_at_k(ranked_ids, relevant, 10),
        "irrelevant_in_top5": [cid for cid in ranked_ids[:5] if cid not in relevant],
        "missed_evidence": sorted(relevant - set(ranked_ids)),
    }

    # ---- Evidence orchestrator ----
    t0 = time.perf_counter()
    pack = await _eo_orchestrator.orchestrate(result, plan, _eo_config)
    eo_latency_ms = (time.perf_counter() - t0) * 1000.0
    pack_doc_ids = {item.doc_id for item in pack.items}
    pack_chunk_ids = [item.chunk_id for item in pack.items]
    expected_docs = set(q.expected_source_doc_ids)
    record["evidence"] = {
        "item_count": len(pack.items),
        "raw_candidate_count": pack.raw_candidate_count,
        "token_reduction_ratio": pack.token_reduction_ratio,
        "doc_ids_present": sorted(pack_doc_ids),
        "expected_doc_ids": sorted(expected_docs),
        "doc_coverage": (
            len(expected_docs & pack_doc_ids) / len(expected_docs) if expected_docs else None
        ),
        "duplicate_chunk_ids": [
            cid for cid in set(pack_chunk_ids) if pack_chunk_ids.count(cid) > 1
        ],
        "dedup_method_used": pack.trace.dedup_method_used,
        "latency_ms": eo_latency_ms,
    }

    # ---- Context builder ----
    t0 = time.perf_counter()
    context = await _cb_pipeline.build(pack, _cb_config)
    cb_latency_ms = (time.perf_counter() - t0) * 1000.0
    block_texts = [b.text for b in context.ordered_blocks]
    lost_chunks = [
        cid
        for cid in q.relevant_chunk_ids
        if cid in pack_chunk_ids
        and not any(CORPUS_BY_ID[cid].text[:20] in t for t in block_texts)
    ]
    record["context"] = {
        "blocks_included": len(context.ordered_blocks),
        "items_dropped": context.metadata.items_dropped,
        "items_compressed": context.metadata.items_compressed,
        "token_count": context.token_count,
        "budget_total": context.metadata.budget_total,
        "token_utilization": (
            context.token_count / context.metadata.budget_total
            if context.metadata.budget_total
            else None
        ),
        "conflicts_detected": context.metadata.conflicts_detected,
        "conflict_groups": len(context.conflicts),
        "lost_relevant_chunks_after_evidence": lost_chunks,
        "latency_ms": cb_latency_ms,
    }

    # ---- Answer generation (MockLLM) ----
    llm = _mock_llm_for(q, context)
    ag_pipeline = AnswerGenerationRegistry.build(_ag_config, llm)
    t0 = time.perf_counter()
    answer_result = await ag_pipeline.run(context=context, question=q.text, config=_ag_config)
    ag_latency_ms = (time.perf_counter() - t0) * 1000.0
    record["answer"] = {
        "no_answer": answer_result.no_answer,
        "answer_text": answer_result.answer,
        "citation_count": len(answer_result.citations),
        "grounding_flags": [f.reason for f in answer_result.grounding_flags],
        "conflicts_disclosed": answer_result.conflicts_disclosed,
        "latency_ms": ag_latency_ms,
    }

    # ---- Answer quality scorers (real scorer code) ----
    fixture = GoldenTestFixture(
        question_id=q.query_id,
        question=q.text,
        expected_source_ids=q.expected_source_doc_ids or None,
        expected_answer_facets=q.expected_answer_facets or None,
    )
    snapshot = PipelineSnapshot(
        question_id=q.query_id,
        answer_result=answer_result,
        context=context,
        evidence_pack=pack,
    )
    runner = AnswerQualityRegistry.default_runner()
    aq_config = AnswerQualityConfig()
    eval_result = await runner.run([fixture], [snapshot], aq_config, fixture_file="eval_run/corpus.py")
    qr = eval_result.question_results[0]
    record["quality"] = {
        "coverage_score": qr.coverage.coverage_score,
        "coverage_passed": qr.coverage.passed,
        "missing_source_ids": qr.coverage.missing_source_ids,
        "faithfulness_score": qr.faithfulness.faithfulness_score,
        "faithfulness_passed": qr.faithfulness.passed,
        "unsupported_claims": qr.faithfulness.unsupported_claims,
        "completeness_score": qr.completeness.completeness_score,
        "completeness_passed": qr.completeness.passed,
        "uncovered_facets": qr.completeness.uncovered_facets,
        "overall_passed": qr.passed,
    }
    return record


async def main() -> None:
    records = [await run_query(q) for q in QUERIES]
    out_path = Path(__file__).resolve().parent / "results_pipeline.json"
    out_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")

    # ---- Aggregate summary ----
    def _agg(key_path: list[str]) -> list[float]:
        vals = []
        for r in records:
            node = r
            for k in key_path:
                if node is None:
                    break
                node = node.get(k)
            if isinstance(node, (int, float)):
                vals.append(node)
        return vals

    summary = {}
    for metric in [
        "recall_at_5",
        "recall_at_10",
        "recall_at_20",
        "precision_at_5",
        "precision_at_10",
        "mrr",
        "ndcg_at_10",
    ]:
        vals = _agg(["retrieval", metric])
        summary[metric] = {
            "n": len(vals),
            "mean": statistics.mean(vals) if vals else None,
        }

    for metric in ["coverage_score", "faithfulness_score", "completeness_score"]:
        vals = _agg(["quality", metric])
        summary[metric] = {
            "n": len(vals),
            "mean": statistics.mean(vals) if vals else None,
        }

    for stage, key in [
        ("planner_latency_ms", ["planner", "latency_ms"]),
        ("retrieval_latency_ms", ["retrieval", "latency_ms"]),
        ("evidence_latency_ms", ["evidence", "latency_ms"]),
        ("context_latency_ms", ["context", "latency_ms"]),
        ("answer_latency_ms", ["answer", "latency_ms"]),
    ]:
        vals = _agg(key)
        summary[stage] = {"n": len(vals), "mean": statistics.mean(vals) if vals else None}

    intent_correct = sum(1 for r in records if r["planner"]["intent_correct"])
    summary["planner_intent_accuracy"] = intent_correct / len(records)
    clarifications = sum(1 for r in records if r["planner"]["clarification_required"])
    summary["clarification_rate"] = clarifications / len(records)

    print(json.dumps(summary, indent=2))
    summary_path = Path(__file__).resolve().parent / "results_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
