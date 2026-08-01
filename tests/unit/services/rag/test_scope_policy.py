from services.rag.adapters.scope import (
    ScopeMissReason,
    apply_field_score_boost,
    classify_scoped_miss,
    merge_retrieved_docs,
    per_entity_fetch_limit,
    resolve_entity_prefixes,
)
from stores.vectordb.providers.pgvector.search import (
    _build_scope_where,
    _build_scoped_bm25_query,
    _build_tsquery,
    _entity_scope_tokens,
)


def test_entity_scope_tokens_drop_dose_form_noise():
    tokens = _entity_scope_tokens("Mediquick Ibuprofen 200 mg tablets")
    assert tokens == ["MEDIQUICK", "IBUPROFEN"]


def test_entity_scope_tokens_keep_panadol_product_line():
    from stores.vectordb.providers.pgvector.search import brand_head_fallback_prefix

    advance = _entity_scope_tokens("Panadol Advance 500")
    extra = _entity_scope_tokens("Panadol Extra")
    assert advance == ["PANADOL", "ADVANCE"]
    assert extra == ["PANADOL", "EXTRA"]
    assert advance != extra
    assert brand_head_fallback_prefix("Panadol Advance 500") == "PANADOL"
    assert brand_head_fallback_prefix("Panadol") is None


def test_build_tsquery_strips_punctuation():
    q = (
        "pregnant 32 weeks with backache and blocked nose. evaluate separately: "
        "brufen, cataflam, otrivin 0.1%, panadol, flurest-n. which are typically "
        "avoided late pregnancy and why?"
    )
    ts = _build_tsquery(q)
    assert "nose.:*" not in ts
    assert "brufen,:*" not in ts
    assert "0.1%,:*" not in ts
    assert "why?:*" not in ts
    assert "separately::*" not in ts
    assert "flurest-n.:*" not in ts
    assert "pregnant:*" in ts.casefold()
    assert "32:*" not in ts
    assert "with:*" not in ts.casefold()
    assert "and:*" not in ts.casefold()


def test_scoped_bm25_query_focuses_field_and_entity():
    focused = _build_scoped_bm25_query(
        "pregnant 32 weeks with backache and blocked nose. evaluate separately: "
        "brufen, cataflam. which are typically avoided late pregnancy and why?",
        entity_prefix="BRUFEN",
        field_key="pregnancy",
    )
    assert "pregnancy" in focused.casefold()
    assert "brufen" in focused.casefold()
    assert "0.1%" not in focused
    ts = _build_tsquery(focused)
    assert "brufen,:*" not in ts
    assert "pregnancy:*" in ts.casefold()
    assert "brufen:*" in ts.casefold()

    soft = _build_scoped_bm25_query(
        "pregnant 32 weeks backache why?",
        entity_prefix="BRUFEN",
        field_key=None,
    )
    assert soft.casefold() == "brufen"
    assert "pregnant" not in soft.casefold()


def test_build_scope_where_ors_multiple_entities():
    where, params = _build_scope_where(
        entity_key="entity",
        entity_prefixes=["BRUFEN", "CATAFLAM", "OTRIVIN", "PANADOL", "FLUREST-N"],
        field_key=None,
    )
    assert " OR " in where
    values = list(params.values())
    assert "%BRUFEN%" in values
    assert "%CATAFLAM%" in values
    assert "%OTRIVIN%" in values
    assert "%PANADOL%" in values
    assert "%FLUREST%" in values


def test_multi_entity_fanout_helpers():
    prefixes = resolve_entity_prefixes(
        {
            "entity_prefix": "BRUFEN",
            "entity_prefixes": ["BRUFEN", "CATAFLAM", "OTRIVIN"],
        }
    )
    assert prefixes == ["BRUFEN", "CATAFLAM", "OTRIVIN"]
    assert per_entity_fetch_limit(30, 5) == 6

    class _D:
        def __init__(self, score, text):
            self.score = score
            self.text = text

    merged = merge_retrieved_docs(
        [
            [_D(0.9, "cataflam pregnancy"), _D(0.8, "cataflam dose")],
            [_D(0.7, "brufen header"), _D(0.9, "cataflam pregnancy")],
        ],
        limit=10,
    )
    texts = [d.text for d in merged]
    assert "brufen header" in texts
    assert texts.count("cataflam pregnancy") == 1


class _Doc:
    def __init__(self, score, metadata, text=""):
        self.score = score
        self.metadata = metadata
        self.text = text


def test_classify_metadata_missing_when_prefix_without_key():
    reason = classify_scoped_miss(
        {"entity_prefix": "ibuprofen", "entity_key": None, "field_key": "dosage"}
    )
    assert reason == ScopeMissReason.METADATA_MISSING


def test_classify_entity_not_found_when_complete_scope_empty():
    reason = classify_scoped_miss(
        {
            "entity_prefix": "ibuprofen",
            "entity_key": "entity",
            "field_key": "contraindications",
        }
    )
    assert reason == ScopeMissReason.ENTITY_NOT_FOUND


def test_classify_entity_not_found_for_multi_entity_prefixes():
    reason = classify_scoped_miss(
        {
            "entity_prefix": None,
            "entity_prefixes": ["BRUFEN", "CATAFLAM"],
            "entity_key": "entity",
            "field_key": "pregnancy",
        }
    )
    assert reason == ScopeMissReason.ENTITY_NOT_FOUND


def test_field_score_boost_prefers_matching_field():
    docs = [
        _Doc(0.5, {"field_name": "interactions"}, "warfarin interaction"),
        _Doc(0.48, {"field_name": "contraindications"}, "do not take if pregnant"),
    ]
    ranked = apply_field_score_boost(docs, field_key="contraindications", boost=0.2)
    assert ranked[0].metadata["field_name"] == "contraindications"
    assert ranked[0].score > ranked[1].score
