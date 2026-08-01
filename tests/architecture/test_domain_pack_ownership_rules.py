"""T037 — Domain Packs own domain vocabulary; not core orchestration."""

from __future__ import annotations

from tests.architecture._repo import GOV, markdown_table_rows, read


def _owner(concern_id: str) -> str:
    rows = markdown_table_rows(read(GOV / "ownership-registry.md"))
    header = [h.lower() for h in rows[0]]
    id_i = header.index("concern_id")
    owner_i = header.index("owner")
    for row in rows[1:]:
        if row[id_i] == concern_id:
            return row[owner_i]
    raise AssertionError(f"Missing concern {concern_id}")


def test_domain_vocabulary_owned_by_domain_packs() -> None:
    owner = _owner("domain_vocabulary")
    assert "Domain Pack" in owner


def test_composition_wiring_owned_by_composition() -> None:
    owner = _owner("composition_wiring")
    assert owner.strip() == "Composition"


def test_core_orchestration_not_owned_by_domain_packs() -> None:
    for concern in (
        "retrieval_execution",
        "answer_generation",
        "chunking_embed_text",
        "composition_wiring",
    ):
        owner = _owner(concern)
        assert "Domain Pack" not in owner, f"{concern} incorrectly owned by Domain Packs"
