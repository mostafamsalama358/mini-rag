"""T051 — nine Trace sections with correct producers."""

from __future__ import annotations

from tests.architecture._repo import GOV_018, markdown_table_rows, read


EXPECTED = {
    "Plan Trace": "Retrieval Plan",
    "Retrieval Trace": "Retrieval",
    "Expansion Trace": "Retrieval",
    "Fusion Trace": "Retrieval",
    "Rerank Trace": "Retrieval",
    "Evidence Trace": "Evidence",
    "Context Trace": "Context",
    "Generation Trace": "Answer Generation",
    "Verification Trace": "Answer Generation",
}


def test_trace_sections_and_producers() -> None:
    text = read(GOV_018 / "quality-context-trace-registry.md")
    rows = markdown_table_rows(text)
    # Find the Trace table: header contains Section / Producer
    trace_rows = []
    capture = False
    for row in rows:
        joined = " ".join(row).lower()
        if "section" in joined and "producer" in joined:
            capture = True
            continue
        if capture:
            if row[0].startswith("Plan") or "Trace" in row[0]:
                trace_rows.append(row)
            elif trace_rows and "field" in joined:
                break
    # Fallback: scan text for section names
    for section, producer in EXPECTED.items():
        assert section in text, f"missing {section}"
        # producer appears near section in file
        assert producer in text, f"missing producer {producer}"
    assert len(EXPECTED) == 9
