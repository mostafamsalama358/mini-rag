"""Shared fixtures for Answer Quality unit tests."""

from __future__ import annotations

import pytest

from core.answer_generation.models import AnswerResult
from core.answer_quality.config import AnswerQualityConfig
from core.answer_quality.models import GoldenTestFixture, ScoreThresholds
from core.context_builder.models import (
    Context,
    ContextBlock,
    ContextMetadata,
)
from core.evidence_orchestrator.models import (
    Citation,
    EvidenceItem,
    EvidenceItemSource,
    EvidencePack,
    OrchestratorTrace,
    compute_item_id,
    compute_pack_id,
)
from tests.unit.core.context_builder.conftest import make_item, make_pack


def _citation(**kwargs) -> Citation:
    defaults = {
        "document_id": "doc1",
        "chunk_id": "chunk1",
        "retrieval_score": 0.8,
        "score_source": "fusion",
    }
    defaults.update(kwargs)
    return Citation(**defaults)


@pytest.fixture
def default_config() -> AnswerQualityConfig:
    return AnswerQualityConfig()


def build_evidence_pack(
    doc_ids: list[str] | None = None,
    *,
    plan_id: str = "plan_test001",
) -> EvidencePack:
    doc_ids = doc_ids or []
    items = [
        make_item(doc_id=doc_id, chunk_id=f"chunk_{index}", text=f"Text for {doc_id}.")
        for index, doc_id in enumerate(doc_ids)
    ]
    return make_pack(items, plan_id=plan_id)


def build_context(
    block_texts: list[str] | None = None,
    *,
    plan_id: str = "plan_test001",
) -> Context:
    block_texts = block_texts or []
    blocks: list[ContextBlock] = []
    citation_map: dict[str, Citation] = {}
    for index, text in enumerate(block_texts):
        item_id = compute_item_id(f"chunk_{index}", f"doc_{index}")
        blocks.append(
            ContextBlock(
                item_id=item_id,
                document_id=f"doc_{index}",
                text=text,
                token_count=max(1, len(text.split())),
            )
        )
        citation_map[item_id] = _citation(
            document_id=f"doc_{index}",
            chunk_id=f"chunk_{index}",
        )
    token_count = sum(block.token_count for block in blocks)
    return Context(
        context_id="ctx_test0000000001",
        pack_id=compute_pack_id(plan_id, "2026-07-14T12:00:00Z"),
        plan_id=plan_id,
        ordered_blocks=blocks,
        citation_map=citation_map,
        token_count=token_count,
        metadata=ContextMetadata(
            items_included=len(blocks),
            items_dropped=0,
            items_compressed=0,
            budget_total=4000,
            budget_used=token_count,
        ),
        created_at="2026-07-14T12:00:00Z",
    )


def build_answer_result(
    answer: str = "Sample answer text.",
    *,
    no_answer: bool = False,
    plan_id: str = "plan_test001",
    context_id: str = "ctx_test0000000001",
) -> AnswerResult:
    return AnswerResult(
        answer=answer,
        no_answer=no_answer,
        plan_id=plan_id,
        context_id=context_id,
    )


def build_golden_fixture(
    question_id: str,
    expected_source_ids: list[str] | None = None,
    expected_answer_facets: list[str] | None = None,
    *,
    question: str = "Test question?",
    thresholds: ScoreThresholds | None = None,
) -> GoldenTestFixture:
    return GoldenTestFixture(
        question_id=question_id,
        question=question,
        expected_source_ids=expected_source_ids,
        expected_answer_facets=expected_answer_facets,
        thresholds=thresholds,
    )
