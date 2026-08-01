"""T019 — required data-model entities appear in quality-entity-catalog."""

from __future__ import annotations

from tests.architecture._repo import DATA_MODEL_018, GOV_018, read


REQUIRED_ENTITIES = [
    "UnderstoodQuery",
    "RetrievalPlan",
    "CandidateLifecycle",
    "EvidencePack",
    "Context",
    "AnswerResult",
    "QualityContext",
    "QualityTrace",
]


def test_entity_catalog_covers_data_model_core() -> None:
    catalog = read(GOV_018 / "quality-entity-catalog.md")
    model = read(DATA_MODEL_018)
    for name in REQUIRED_ENTITIES:
        assert name in model, f"{name} missing from data-model.md"
        assert name in catalog, f"{name} missing from quality-entity-catalog.md"
