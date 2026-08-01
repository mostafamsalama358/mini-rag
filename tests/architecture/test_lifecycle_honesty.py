"""T027 — docs do not claim production-complete for pending/research capabilities."""

from __future__ import annotations

from tests.architecture._repo import AGENTS, ARCHITECTURE, GOV, markdown_table_rows, read


def _non_production_subjects() -> list[str]:
    rows = markdown_table_rows(read(GOV / "lifecycle-registry.md"))
    header = [h.lower() for h in rows[0]]
    id_i = header.index("subject_id")
    state_i = header.index("lifecycle_state")
    out: list[str] = []
    for row in rows[1:]:
        state = row[state_i].lower()
        if any(
            s in state
            for s in (
                "activation_pending",
                "dormant",
                "research_capability",
            )
        ):
            out.append(row[id_i])
    return out


def test_structured_knowledge_is_activation_pending() -> None:
    text = read(GOV / "lifecycle-registry.md").lower()
    assert "structured_knowledge" in text
    assert "activation_pending_consumer" in text


def test_agents_does_not_mark_pending_subjects_complete() -> None:
    agents = read(AGENTS).lower()
    for subject in _non_production_subjects():
        # Forbid "dependency (complete)" adjacent claims for pending subjects
        needle = subject.replace("_", " ")
        if subject in agents or needle in agents:
            assert "dependency (complete)" not in agents or subject not in agents
        assert f"{subject}` — **dependency (complete)**".lower() not in agents


def test_architecture_guide_mentions_consolidation_governance() -> None:
    arch = read(ARCHITECTURE)
    assert "016" in arch or "Architecture Consolidation" in arch
