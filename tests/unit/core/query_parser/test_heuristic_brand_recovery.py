from core.query_parser.parser import (
    _heuristic_plan_from_query,
    _recover_latin_brand_entity,
)


def test_recover_skips_already_prefers_buscopan_plus():
    q = (
        "Patient already took 3 g of paracetamol today from various cold products. "
        "Can they still take Buscopan Plus tonight for abdominal cramp? Why/why not?"
    )
    assert _recover_latin_brand_entity(q) == "Buscopan Plus"


def test_recover_panadol_advance_product_line():
    assert _recover_latin_brand_entity("Panadol Advance 500 twice daily") == "Panadol Advance"


def test_heuristic_buscopan_stacking_question():
    q = (
        "Patient already took 3 g of paracetamol today from various cold products. "
        "Can they still take Buscopan Plus tonight for abdominal cramp? Why/why not?"
    )
    result = _heuristic_plan_from_query(
        q,
        language="en",
        catalog_terms=None,
        fingerprint_index=None,
        min_score=0.55,
    )
    assert result is not None
    plan, _canonical = result
    assert plan.entity == "Buscopan Plus"
    assert plan.field == "interactions"
