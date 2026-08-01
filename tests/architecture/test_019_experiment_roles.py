"""T048 — experiment roles complete."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, markdown_table_rows, read


REQUIRED = {"Baseline", "Candidate", "Champion", "Challenger", "Shadow", "Canary"}


def test_experiment_roles_complete() -> None:
    rows = markdown_table_rows(read(GOV_019 / "experiment-role-catalog.md"))
    roles = {r[0].strip() for r in rows[1:]}
    missing = sorted(REQUIRED - roles)
    assert not missing, f"Missing experiment roles: {missing}"
