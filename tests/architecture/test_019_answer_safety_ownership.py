"""T034 — answer safety metrics owned by Answer Generation."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, markdown_table_rows, read


def test_answer_safety_owned_by_answer_generation() -> None:
    rows = markdown_table_rows(read(GOV_019 / "metric-ownership-registry.md"))
    by_metric = {r[0].strip(): r[1].strip() for r in rows[1:]}
    for metric in (
        "Faithfulness",
        "Groundedness",
        "Citation Accuracy",
        "Hallucination Rate",
    ):
        assert by_metric[metric] == "Answer Generation"
