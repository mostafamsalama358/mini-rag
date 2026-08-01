"""T017 — one canonical role per concept."""

from __future__ import annotations

from collections import Counter

from tests.architecture._repo import GOV, markdown_table_rows, read


def test_one_role_per_concept() -> None:
    rows = markdown_table_rows(read(GOV / "contract-role-catalog.md"))
    header = [h.lower() for h in rows[0]]
    concept_i = header.index("concept")
    concepts = [row[concept_i] for row in rows[1:] if len(row) > concept_i]
    assert concepts, "contract-role catalog empty"
    counts = Counter(concepts)
    dupes = {c: n for c, n in counts.items() if n > 1}
    assert not dupes, f"Duplicate concepts in contract-role catalog: {dupes}"
