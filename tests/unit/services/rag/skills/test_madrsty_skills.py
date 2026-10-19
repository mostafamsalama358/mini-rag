"""Madrsty Domain Pack — subject → intent Skills (one skill_id)."""

from __future__ import annotations

from services.FieldRegistry import FieldRegistry
from services.rag.metadata_enrichment import enrich_chunk_metadata, overlay_document_attributes
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
    assert subjects == {"geography", "french", "statistics", "psychology", "science"}
    geo = [row for row in catalog if row["subject"] == "geography"]
    assert [row["intent"] for row in geo] == [
        "explain",
        "summary",
        "example",
        "exercise",
        "map",
    ]
    stats = [row for row in catalog if row["subject"] == "statistics"]
    assert [row["intent"] for row in stats] == [
        "explain",
        "summary",
        "example",
        "exercise",
        "formula",
    ]
    psych = [row for row in catalog if row["subject"] == "psychology"]
    assert [row["intent"] for row in psych] == [
        "explain",
        "summary",
        "example",
        "exercise",
    ]
    science = [row for row in catalog if row["subject"] == "science"]
    assert [row["intent"] for row in science] == [
        "explain",
        "summary",
        "example",
        "exercise",
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


def test_filename_detector_sets_statistics_subject():
    profile = _madrsty()
    meta = enrich_chunk_metadata(
        {
            "file_name": "كتاب الطالب احصاء للصف الحادي عشر الفصل الاول.pdf",
            "page": 12,
        },
        "المتوسط الحسابي لمجموعة من القيم.",
        enrichment=profile.metadata,
    )
    assert meta.get("subject") == "statistics"
    assert meta.get("grade") == "11"
    assert "الإحصاء" in (meta.get("book") or "")


def test_filename_detector_sets_psychology_subject():
    profile = _madrsty()
    meta = enrich_chunk_metadata(
        {
            "file_name": "كتاب علم النفس وعلم الاجتماع للصف الحادي عشر الفصل الاول.pdf",
            "page": 20,
        },
        "تعريف علم النفس ومجالاته.",
        enrichment=profile.metadata,
    )
    assert meta.get("subject") == "psychology"
    assert "النفس" in (meta.get("book") or "")


def test_filename_detector_sets_psychology_subject_when_spaces_stripped():
    profile = _madrsty()
    meta = enrich_chunk_metadata(
        {
            "file_name": "0f056evrh64h_كتابعلمالنفسوعلمالاجتماعللصفالحاديعشرالفصلالاول.pdf",
            "page": 20,
        },
        "تعريف علم النفس ومجالاته.",
        enrichment=profile.metadata,
    )
    assert meta.get("subject") == "psychology"


def test_statistics_explain_filters_subject_only():
    ctx = resolve_skill(_madrsty(), "statistics_explain")
    assert ctx is not None
    assert not ctx.metadata_filters.get("field")
    assert jsonb_metadata_filter(ctx.metadata_filters) == {"subject": "statistics"}


def test_science_explain_keeps_client_grade():
    ctx = resolve_skill(_madrsty(), "science_explain")
    assert ctx is not None
    merged = ctx.merge_client_filters({"grade": "G8a"})
    assert jsonb_metadata_filter(merged) == {"grade": "G8a", "subject": "science"}


def test_filename_detector_sets_science_without_grade():
    profile = _madrsty()
    meta = enrich_chunk_metadata(
        {"file_name": "abc_علوم.pdf", "page": 3},
        "الخلية وحدة البناء.",
        enrichment=profile.metadata,
    )
    assert meta.get("subject") == "science"
    assert "grade" not in meta


def test_upload_attributes_set_class_on_shared_filename():
    meta = overlay_document_attributes(
        {"file_name": "علوم.pdf", "subject": "science", "book": "العلوم"},
        {"subject": "science", "grade": "G9a", "book": "العلوم — G9a"},
    )
    assert meta["grade"] == "G9a"
    assert meta["book"] == "العلوم — G9a"
    assert meta["subject"] == "science"


def test_madrsty_classes_list_g8_and_g9():
    pack = FieldRegistry().load().get_pack("madrsty")
    ids = [item["id"] for item in pack.classes]
    assert ids == ["11", "G8a", "G9a"]
    g8 = next(item for item in pack.classes if item["id"] == "G8a")
    assert "science" in [subject["id"] for subject in g8["subjects"]]
    assert "english" in [subject["id"] for subject in g8["subjects"]]
