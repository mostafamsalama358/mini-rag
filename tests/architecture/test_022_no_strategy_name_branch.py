"""022 — retrieval engine must not branch on strategy name strings."""

from __future__ import annotations

from tests.architecture._repo import REPO_ROOT

ANSWER = REPO_ROOT / "src" / "services" / "rag" / "answer_service.py"


def test_answer_service_no_strategy_name_equality() -> None:
    text = ANSWER.read_text(encoding="utf-8")
    banned = (
        'strategy_name == "pair_lookup"',
        'retrieval_strategy == "pair_lookup"',
        'if strategy == "pair_lookup"',
    )
    hits = [pat for pat in banned if pat in text]
    assert not hits, f"Strategy name branching in answer_service: {hits}"
