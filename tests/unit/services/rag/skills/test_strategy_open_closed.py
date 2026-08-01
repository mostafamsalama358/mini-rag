"""US3 — new strategy registers without editing retrieval stage."""

from __future__ import annotations

from pathlib import Path

from services.rag.skills.strategies import StrategyRegistry
from services.rag.skills.strategies.base import RetrievalStrategy


class _Custom:
    name = "custom_fixture"

    async def retrieve(self, *, ctx, **kwargs):
        return [{"id": "c"}], "custom_fixture"


def test_register_strategy_without_touching_retrieval_stage() -> None:
    registry = StrategyRegistry()
    registry.register(_Custom())
    assert registry.get("custom_fixture").name == "custom_fixture"

    repo = Path(__file__).resolve().parents[5]
    retrieval_stage = (
        repo / "src" / "services" / "rag" / "skills" / "stages" / "retrieval.py"
    )
    text = retrieval_stage.read_text(encoding="utf-8")
    assert "custom_fixture" not in text
    assert "get_retrieval_strategy" in text or "retrieve_via_strategy" in text
