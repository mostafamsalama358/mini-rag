"""T029 — standard slice dimensions present."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, markdown_table_rows, read


REQUIRED = {
    "domain",
    "language",
    "intent",
    "query complexity",
    "retrieval strategy",
    "planner strategy",
    "document type",
    "tenant",
    "context size",
    "answer length",
    "dataset tier",
}


def test_slice_dimensions_present() -> None:
    rows = markdown_table_rows(read(GOV_019 / "slice-dimension-catalog.md"))
    dims = {r[0].strip().lower() for r in rows[1:]}
    missing = sorted(REQUIRED - dims)
    assert not missing, f"Missing slice dimensions: {missing}"
