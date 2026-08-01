"""T019 — PR profile requires Frozen Core Golden."""

from __future__ import annotations

from tests.architecture._repo import GOV_019, markdown_table_rows, read


def test_pr_profile_requires_frozen_core() -> None:
    text = read(GOV_019 / "evaluation-profile-index.md")
    assert "Frozen Core" in text or "Frozen Core Golden" in text
    rows = markdown_table_rows(text)
    assert rows
    header = [h.lower() for h in rows[0]]
    profile_idx = 0
    freeze_idx = next(i for i, h in enumerate(header) if "freeze" in h)
    pr_rows = [r for r in rows[1:] if r[profile_idx].strip() == "PR"]
    assert pr_rows, "PR profile row missing"
    freeze_cell = pr_rows[0][freeze_idx]
    assert "yes" in freeze_cell.lower() and "frozen" in freeze_cell.lower()
