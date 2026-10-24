"""Madrsty Domain Pack — subject → intent Skills (one skill_id)."""

from __future__ import annotations

import pytest

from helpers.config import Settings
from services.FieldRegistry import FieldRegistry
from fields.madrsty.scope import MadrstyScopeError, validate_madrsty_retrieval_scope
from services.rag.metadata_enrichment import enrich_chunk_metadata, overlay_document_attributes
from services.rag.skills import list_skill_catalog, resolve_skill
from services.rag.skills.filters import jsonb_metadata_filter
from utils.idempotency_manager import stuck_task_window_seconds
from utils.project_assets import build_asset_fingerprint

CANONICAL_GRADES = [
    "G0",
    "G1",
    "G2",
    "G3",
    "G4",
    "G5",
    "G6",
    "G7",
    "G8",
    "G9",
    "G10",
    "G11_SCI",
    "G11_LIT",
    "G12_SCI",
    "G12_LIT",
    "G12_REL",
    "UNI_MED",
    "UNI_PHARM",
    "UNI_ENG",
    "UNI_INST",
    "APT_EN",
]


def _madrsty():
    return FieldRegistry().load().build_profile("madrsty")


def test_madrsty_pack_loads_and_catalog_is_grouped():
    profile = _madrsty()
    catalog = list_skill_catalog(profile)
    ids = {row["id"] for row in catalog}
    assert "science_explain" in ids
    assert "french_culture" in ids
    assert all(row.get("subject") for row in catalog)
    subjects = {row["subject"] for row in catalog}
    assert "science" in subjects
    assert "french" in subjects
    science = [row for row in catalog if row["subject"] == "science"]
    assert [row["intent"] for row in science] == [
        "explain",
        "summary",
        "example",
        "exercise",
    ]
    french = [row for row in catalog if row["subject"] == "french"]
    french_intents = [row["intent"] for row in french]
    assert "culture" in french_intents
    assert "grammar" in french_intents


def test_every_catalog_subject_has_a_skill():
    pack = FieldRegistry().load().get_pack("madrsty")
    skilled = {skill.subject for skill in pack.skills.values() if skill.subject}
    catalog_subjects = {
        subject["id"]
        for item in pack.classes
        for subject in item["subjects"]
    }
    assert catalog_subjects <= skilled
    math_intents = [
        row["intent"]
        for row in list_skill_catalog(_madrsty())
        if row["subject"] == "math"
    ]
    assert math_intents[:4] == ["explain", "summary", "example", "exercise"]
    assert "formula" in math_intents


def test_pharmacy_catalog_stays_flat():
    pharmacy = FieldRegistry().load().build_profile("pharmacy")
    catalog = list_skill_catalog(pharmacy)
    assert catalog
    assert all("subject" not in row for row in catalog)


def test_french_culture_filters_subject_only():
    ctx = resolve_skill(_madrsty(), "french_culture")
    assert ctx is not None
    assert ctx.skill_id == "french_culture"
    assert ctx.metadata_filters["extra"]["subject"] == "french"
    assert ctx.retrieval_strategy == "default"
    assert jsonb_metadata_filter(ctx.metadata_filters) == {"subject": "french"}


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
    assert "grade" not in meta
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
    assert "grade" not in meta
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


def test_science_explain_keeps_client_grade():
    ctx = resolve_skill(_madrsty(), "science_explain")
    assert ctx is not None
    merged = ctx.merge_client_filters({"grade": "G8"})
    assert jsonb_metadata_filter(merged) == {"grade": "G8", "subject": "science"}


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
        {"subject": "science", "grade": "G9", "book": "العلوم — G9"},
    )
    assert meta["grade"] == "G9"
    assert meta["book"] == "العلوم — G9"
    assert meta["subject"] == "science"


def test_upload_aliases_copy_canonical_keys():
    meta = overlay_document_attributes(
        {"file_name": "علوم.pdf"},
        {
            "classId": "G8",
            "subjectId": "science",
            "contentId": "cid-1",
            "contentType": "pdf",
            "unitId": "unit-1",
            "lessonId": "lesson-1",
            "checksumSha256": "abc123",
            "contentVersion": 3,
        },
    )
    assert meta["grade"] == "G8"
    assert meta["subject"] == "science"
    assert meta["content_id"] == "cid-1"
    assert meta["content_type"] == "pdf"
    assert meta["unit_id"] == "unit-1"
    assert meta["lesson_id"] == "lesson-1"
    assert meta["checksum_sha256"] == "abc123"
    assert meta["content_version"] == 3


def test_upload_copies_curriculum_scope():
    meta = overlay_document_attributes(
        {},
        {
            "countryId": "KW",
            "sectionId": "arabic_schools",
            "stageId": "primary",
            "semesterId": "1",
            "attachmentId": "att-1",
        },
    )
    assert meta["country"] == "KW"
    assert meta["section"] == "arabic_schools"
    assert meta["stage"] == "primary"
    assert meta["semester"] == "1"
    assert meta["attachment_id"] == "att-1"


def test_filename_detector_does_not_overwrite_uploaded_grade_or_subject():
    profile = _madrsty()
    uploaded = overlay_document_attributes(
        {"file_name": "اللغة-الفرنسية-كتاب-الطالب.pdf", "page": 4},
        {"grade": "G8", "subject": "science", "book": "العلوم — G8"},
    )
    meta = enrich_chunk_metadata(
        uploaded,
        "الخلية وحدة البناء.",
        enrichment=profile.metadata,
    )
    assert meta["grade"] == "G8"
    assert meta["subject"] == "science"
    assert meta["book"] == "العلوم — G8"


def test_madrsty_classes_use_canonical_grades():
    pack = FieldRegistry().load().get_pack("madrsty")
    ids = [item["id"] for item in pack.classes]
    assert ids == CANONICAL_GRADES
    assert "11" not in ids
    g8 = next(item for item in pack.classes if item["id"] == "G8")
    g8_subjects = [subject["id"] for subject in g8["subjects"]]
    assert "science" in g8_subjects
    assert "english" in g8_subjects
    assert "kuwait_world" in g8_subjects
    literary = next(item for item in pack.classes if item["id"] == "G11_LIT")
    literary_subjects = [subject["id"] for subject in literary["subjects"]]
    assert "french" in literary_subjects
    assert "geography" in literary_subjects
    assert "statistics" in literary_subjects
    assert "psychology" in literary_subjects
    scientific = next(item for item in pack.classes if item["id"] == "G12_SCI")
    scientific_subjects = [subject["id"] for subject in scientific["subjects"]]
    assert "physics" in scientific_subjects
    assert "chemistry" in scientific_subjects
    assert "biology" in scientific_subjects
    assert "constitution" in scientific_subjects
    g1 = next(item for item in pack.classes if item["id"] == "G1")
    assert g1["stage"] == "primary"
    g1_subjects = [subject["id"] for subject in g1["subjects"]]
    assert "pe_girls" in g1_subjects
    assert "art" in g1_subjects
    religious = next(item for item in pack.classes if item["id"] == "G12_REL")
    religious_subjects = [subject["id"] for subject in religious["subjects"]]
    assert "tafsir" in religious_subjects
    assert "hadith" in religious_subjects
    assert "fiqh" in religious_subjects
    engineering = next(item for item in pack.classes if item["id"] == "UNI_ENG")
    assert [subject["id"] for subject in engineering["subjects"]] == ["math_2"]
    countries = {row["id"]: row for row in pack.curriculum["countries"]}
    assert countries["KW"]["code"] == "+965"
    assert countries["EG"]["sections"] == []
    school = next(
        row for row in countries["KW"]["sections"] if row["id"] == "arabic_schools"
    )
    assert [row["id"] for row in school["stages"]] == ["primary", "middle", "secondary"]
    assert {row["id"] for row in pack.curriculum["semesters"]} == {"1", "2", "summer"}
    assert {row["id"] for row in pack.curriculum["grades"]} == set(CANONICAL_GRADES)


def test_madrsty_scope_requires_known_grade_and_search_subject():
    classes = FieldRegistry().load().get_pack("madrsty").classes
    validate_madrsty_retrieval_scope(
        domain_key="pharmacy",
        classes=classes,
        metadata_filter=None,
        route="search",
    )
    with pytest.raises(MadrstyScopeError):
        validate_madrsty_retrieval_scope(
            domain_key="madrsty",
            classes=classes,
            metadata_filter=None,
            route="answer",
        )
    with pytest.raises(MadrstyScopeError):
        validate_madrsty_retrieval_scope(
            domain_key="madrsty",
            classes=classes,
            metadata_filter={"grade": "11"},
            route="answer",
        )
    with pytest.raises(MadrstyScopeError):
        validate_madrsty_retrieval_scope(
            domain_key="madrsty",
            classes=classes,
            metadata_filter={"grade": "G8"},
            route="search",
        )
    validate_madrsty_retrieval_scope(
        domain_key="madrsty",
        classes=classes,
        metadata_filter={"grade": "G8", "subject": "science"},
        route="search",
    )
    validate_madrsty_retrieval_scope(
        domain_key="madrsty",
        classes=classes,
        metadata_filter={"grade": "G8"},
        route="answer",
        skill_subject="science",
    )
    with pytest.raises(MadrstyScopeError):
        validate_madrsty_retrieval_scope(
            domain_key="madrsty",
            classes=classes,
            metadata_filter={"grade": "G8", "subject": "math"},
            route="answer",
            skill_subject="science",
        )


class _Asset:
    def __init__(self, asset_id, asset_name, asset_config):
        self.asset_id = asset_id
        self.asset_name = asset_name
        self.asset_config = asset_config


def test_fingerprint_changes_when_content_version_changes():
    original = _Asset(1, "book.pdf", {"checksumSha256": "abc", "contentVersion": 1})
    revised = _Asset(1, "book.pdf", {"checksum_sha256": "abc", "content_version": 2})
    assert build_asset_fingerprint([original]) != build_asset_fingerprint([revised])


def test_stuck_task_window_covers_long_ocr():
    assert stuck_task_window_seconds(120) >= 3600
    assert stuck_task_window_seconds(3600) >= 3600


def test_file_size_ceiling_is_150_mb():
    assert Settings.model_fields["FILE_MAX_SIZE"].default == 150
    assert Settings.model_fields["INGEST_HARD_MAX_BYTES"].default == 150 * 1024 * 1024
    assert Settings.model_fields["MINIRAG_SERVICE_API_KEY"].default == ""
