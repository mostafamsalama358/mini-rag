"""T050 — run metadata fields present."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, markdown_table_rows, read


REQUIRED_FRAGMENTS = [
    "commit",
    "branch",
    "release",
    "prompt version",
    "embedding version",
    "reranker version",
    "retriever version",
    "planner version",
    "model version",
    "configuration fingerprint",
]


def test_run_metadata_fields_present() -> None:
    rows = markdown_table_rows(read(GOV_019 / "evaluation-run-metadata-catalog.md"))
    fields = " ".join(r[0].lower() for r in rows[1:])
    missing = [f for f in REQUIRED_FRAGMENTS if f not in fields]
    assert not missing, f"Missing metadata fields: {missing}"
