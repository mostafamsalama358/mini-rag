"""Unit tests for EvidenceOrchestrator pipeline."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.evidence_orchestrator.models import (
    Citation,
    EvidenceItem,
    EvidenceItemSource,
    EvidencePack,
    compute_item_id,
)
from core.evidence_orchestrator.registry import EvidenceOrchestratorRegistry
from tests.unit.core.evidence_orchestrator.conftest import make_candidate, make_result


@pytest.fixture
def orchestrator():
    return EvidenceOrchestratorRegistry().build_orchestrator()


@pytest.mark.asyncio
async def test_smoke_single_candidate(
    orchestrator, minimal_retrieval_result, minimal_retrieval_plan, default_config
):
    pack = await orchestrator.orchestrate(
        minimal_retrieval_result, minimal_retrieval_plan, default_config
    )
    assert isinstance(pack, EvidencePack)
    assert pack.is_empty is False
    assert len(pack.items) == 1
    item = pack.items[0]
    assert item.citation is not None
    assert item.text
    assert item.relevance_score is not None
    assert pack.schema_version == "1.0.0"


@pytest.mark.asyncio
async def test_empty_candidates(
    orchestrator, minimal_retrieval_plan, default_config
):
    result = make_result([])
    pack = await orchestrator.orchestrate(result, minimal_retrieval_plan, default_config)
    assert pack.is_empty is True
    assert pack.items == []
    assert pack.raw_candidate_count == 0
    assert pack.token_reduction_ratio is None


def test_is_empty_validator_rejects_inconsistent():
    citation = Citation(
        document_id="d1",
        chunk_id="c1",
        retrieval_score=0.5,
        score_source="fusion",
    )
    item = EvidenceItem(
        item_id=compute_item_id("c1", "d1"),
        doc_id="d1",
        chunk_id="c1",
        citation=citation,
        text="text",
        relevance_score=0.5,
        sources=[EvidenceItemSource(strategy_id="semantic", raw_score=0.5)],
    )
    with pytest.raises(ValidationError):
        EvidencePack(
            pack_id="ep_" + "a" * 16,
            plan_id="rp_test",
            items=[item],
            is_empty=True,
            raw_candidate_count=1,
            trace=__import__(
                "core.evidence_orchestrator.models", fromlist=["OrchestratorTrace"]
            ).OrchestratorTrace(),
            created_at="2026-07-14T00:00:00Z",
        )


@pytest.mark.asyncio
async def test_trace_has_six_stages(
    orchestrator, minimal_retrieval_result, minimal_retrieval_plan, default_config
):
    pack = await orchestrator.orchestrate(
        minimal_retrieval_result, minimal_retrieval_plan, default_config
    )
    stages = [s.stage for s in pack.trace.stages]
    assert stages == [
        "collect",
        "deduplicate",
        "expand",
        "compress_flag",
        "prioritize",
        "package",
    ]


@pytest.mark.asyncio
async def test_pack_id_prefix(
    orchestrator, minimal_retrieval_result, minimal_retrieval_plan, default_config
):
    pack = await orchestrator.orchestrate(
        minimal_retrieval_result, minimal_retrieval_plan, default_config
    )
    assert pack.pack_id.startswith("ep_")
