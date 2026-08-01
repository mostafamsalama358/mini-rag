"""T026 — retirement phases require prior sole-owner phases."""

from __future__ import annotations

from tests.architecture._repo import GOV, markdown_table_rows, read


def test_m7_predecessor_requires_sole_owner_gates() -> None:
    rows = markdown_table_rows(read(GOV / "migration-runbook.md"))
    header = [h.lower() for h in rows[0]]
    phase_i = header.index("phase")
    pred_i = next(i for i, h in enumerate(header) if "predecessor" in h)
    m7 = next(row for row in rows[1:] if row[phase_i] == "M7")
    predecessor = m7[pred_i].lower()
    assert "sole-owner" in predecessor or "m1" in predecessor, (
        f"M7 predecessor must require sole-owner gates, got: {m7[pred_i]}"
    )


def test_phases_m0_through_m8_present() -> None:
    text = read(GOV / "migration-runbook.md")
    for phase in (f"M{i}" for i in range(0, 9)):
        assert phase in text, f"Missing phase {phase}"
