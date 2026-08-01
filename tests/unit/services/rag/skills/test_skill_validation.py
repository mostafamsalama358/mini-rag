"""US4 — Interactions validation clarify on missing medicines."""

from __future__ import annotations

from fields.schemas import SkillDefinition

from services.rag.skills.validation import evaluate_skill_validation


def test_pair_required() -> None:
    skill = SkillDefinition(
        id="interactions",
        name="Interactions",
        profile="drug_interactions",
        prompt="x",
        validation={"require_medicine_pair": True},
    )
    ok, msg = evaluate_skill_validation(skill, ["Panadol"])
    assert ok is False
    assert msg


def test_pair_ok() -> None:
    skill = SkillDefinition(
        id="interactions",
        name="Interactions",
        profile="drug_interactions",
        prompt="x",
        validation={"require_medicine_pair": True},
    )
    ok, msg = evaluate_skill_validation(skill, ["Panadol", "Brufen"])
    assert ok is True
    assert msg is None
