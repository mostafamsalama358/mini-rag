"""Madrsty Domain Pack — subject → intent Skills (one skill_id)."""

from __future__ import annotations

from services.FieldRegistry import FieldRegistry
from services.rag.metadata_enrichment import enrich_chunk_metadata
from services.rag.skills import list_skill_catalog, resolve_skill
from services.rag.skills.filters import jsonb_metadata_filter


def _madrsty():
    return FieldRegistry().load().build_profile("madrsty")


def test_madrsty_pack_loads_and_catalog_is_grouped():
    profile = _madrsty()
    catalog = list_skill_catalog(profile)
    ids = {row["id"] for row in catalog}
    assert "geography_explain" in ids
    assert "french_grammar" in ids
    assert all(row.get("subject") for row in catalog)
    subjects = {row["subject"] for row in catalog}
    assert subjects == {"geography", "french"}
    geo = [row for row in catalog if row["subject"] == "geography"]
    assert [row["intent"] for row in geo] == [
        "explain",
        "summary",
        "example",
        "exercise",
        "map",
    ]
    french = [row for row in catalog if row["subject"] == "french"]
    assert "grammar" in [row["intent"] for row in french]


def test_pharmacy_catalog_stays_flat():
    pharmacy = FieldRegistry().load().build_profile("pharmacy")
    catalog = list_skill_catalog(pharmacy)
    assert catalog
    assert all("subject" not in row for row in catalog)


def test_geography_explain_filters_subject_only():
    profile = _madrsty()
    ctx = resolve_skill(profile, "geography_explain")
    assert ctx is not None
    assert ctx.skill_id == "geography_explain"
    assert not ctx.metadata_filters.get("field")
    assert ctx.metadata_filters["extra"]["subject"] == "geography"
    jsonb = jsonb_metadata_filter(ctx.metadata_filters)
    assert jsonb == {"subject": "geography"}


def test_geography_map_does_not_hard_filter_figure():
    ctx = resolve_skill(_madrsty(), "geography_map")
    assert ctx is not None
    assert not ctx.metadata_filters.get("field")
    assert jsonb_metadata_filter(ctx.metadata_filters) == {"subject": "geography"}


def test_french_grammar_resolves():
    ctx = resolve_skill(_madrsty(), "french_grammar")
    assert ctx is not None
    assert ctx.metadata_filters["field"] == ["grammar"]
    assert ctx.metadata_filters["extra"]["subject"] == "french"


def test_filename_detector_sets_french_subject():
    profile = _madrsty()
    meta = enrich_chunk_metadata(
        {
            "file_name": "اللغة-الفرنسية-كتاب-الطالب-للصف-الحادي-عشر-الفصل-الاول.pdf",
            "page": 12,
        },
        "Le passé composé s'emploie avec avoir ou être.",
        enrichment=profile.metadata,
    )
    assert meta.get("subject") == "french"
    assert meta.get("grade") == "11"
    assert meta.get("field_name") == "grammar"


def test_filename_detector_sets_geography_subject():
    profile = _madrsty()
    meta = enrich_chunk_metadata(
        {
            "file_name": "كتاب مبادئ علم الجغرافيا والاقتصاد للصف الحادي عشر الفصل الاول.pdf",
            "page": 40,
        },
        "الضغط الجوي هو وزن عمود الهواء.",
        enrichment=profile.metadata,
    )
    assert meta.get("subject") == "geography"
    assert "الجغرافيا" in (meta.get("book") or "")
